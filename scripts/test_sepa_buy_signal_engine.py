"""米奈尔维尼 SEPA 买入信号与价格边界解耦全息回归测试 (Test SEPA Buy Signal Engine).

严格遵循《全局工程与协作规范》与《全栈工程命名架构与状态空间规范 (08-全栈工程命名架构与状态空间规范.md)》:
1. 真实物理介质底账回放 (Physical Medium Replay): 物理读取 data/google-finance/raw/ 真实落盘行情，严禁纯内存虚拟造假;
2. 金融数学边界与有限责任防御 (Mathematical Defense): 严格断言零价格、负价格、异常除零抛出强类型异常;
3. 空序列与单笔收缩退化性断言: 验证空列表与单次收敛优雅退化为 No_Contraction，杜绝误报;
4. 严格美分级与浮点数临界点测试 (Strict Floating-Point Edge):
   - 现价恰好等于枢轴买点 (200.00)
   - 现价恰好等于追高上限 (210.00)
   - 现价高出追高上限 1 美分 (210.01) 触发 EXTENDED_OVERBOUGHT 拦截
   - RS 评分恰好处于 70.0 门槛临界
5. 米奈尔维尼“深蹲 (Squat) 与逆转恢复”战术场景实测: 验证回落买点下方但守住止损线与均线时的防割肉保护;
6. 单一事实来源 (SSOT) 状态空间元数据注册表完备性断言。
"""

import unittest
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.sepa_buy_signal_engine import (
    SepaBuySignalEngine,
    SepaInputFacts,
    SepaPriceBoundaries,
    SepaBuySignalResult,
    TrendStageState,
    VcpContractionStatus,
    BuySignalTier,
    SEPA_SIGNAL_STATE_REGISTRY,
    get_sepa_state_metadata,
)
from financial_core.engines.market_adaptive_params import SepaAdaptiveParams


class TestSepaBuySignalEngine(unittest.TestCase):
    """测试 SEPA 买入信号引擎与价格解耦机制."""

    def setUp(self):
        self.default_params = SepaAdaptiveParams()
        self.engine = SepaBuySignalEngine(adaptive_params=self.default_params)

        # 构造基准健康的超级成长股输入事实 (符合 Stage 2 且形成 VCP)
        self.healthy_facts = SepaInputFacts(
            ticker="NVDA",
            val_current_price=204.64,
            val_ma_50=185.20,
            val_ma_150=165.40,
            val_ma_200=150.00,
            val_ma_200_20d_ago=145.50,         # 200日线持续抬升
            val_low_52w=115.00,                 # 现价较 52周低点涨幅 > 70% (标准要求 >=30%)
            val_high_52w=210.00,                # 现价距 52周高点回撤仅 2.5% (标准要求 <=25%)
            num_rs_rank=92.0,                   # 相对强度 92 分 (标准要求 >=70)
            val_pivot_price=200.00,             # 枢轴买点价格为 200.00
            pct_recent_contractions=[28.0, 14.0, 6.0, 2.5], # 经典 VCP 4T 收敛
            days_base_duration=56,              # 8 周
            num_current_volume=65000000.0,      # 今日当前成交量 6500万股
            num_avg_volume_50d=35000000.0,      # 50日均成交量 3500万股 (放量 1.85倍)
            num_dryup_volume_min=12000000.0,    # 收敛地量 1200万股 (约为均量 34%, 地量抽干)
            is_eps_accelerating_3q=True,
            is_sales_accelerating_3q=True,
            has_positive_surprise=True,
        )

    def test_physical_medium_real_quote_replay(self):
        """【UT-SEPA-01: 物理介质真实落盘行情回放买入信号核验】

        1. 测试功能与测试点:
           - 验证从磁盘实际 JSON 行情底账提取当前股价与时效，闭环驱动 SEPA 突破买入信号评估。
           - 严禁纯内存虚拟造假，实现物理介质真实落盘行情回放 (Physical Medium Replay)。
           - 验证枢轴买点放量突破信号触发 (PIVOT_TRIGGERED) 及价格风控走廊计算。

        2. 正常函数业务边界与参数契约:
           - val_current_price 必须在 [val_pivot_price, val_extended_limit_price] 闭区间内判定为处于安全买入区间。
           - 刚性止损线为买点下浮 7%，追高上限为买点上浮 5%，3R 保本止盈点为买点 + 3 * 风险敞口。

        3. 测试数据与模拟场景说明:
           - 读取真实行情文件 data/google-finance/raw/20261101T165141_097402Z_NVDA_market_quote.json，提取真实价格 204.64 美元。
           - 模拟 NVDA 突破 200.00 枢轴买点且放量 1.85 倍的经典 Stage 2 爆发场景。

        4. 预期断言与结果验证:
           - 断言物理行情文件存在且 NVDA 现价精确为 204.64。
           - 断言 status_buy_signal 为 PIVOT_TRIGGERED。
           - 断言 val_stop_loss_price == 186.00, val_extended_limit_price == 210.00, val_breakeven_trigger_price == 242.00。
           - 断言 is_within_buy_range 为 True。
        """
        real_quote_path = ROOT / "data" / "google-finance" / "raw" / "20261101T165141_097402Z_NVDA_market_quote.json"
        self.assertTrue(real_quote_path.is_file(), f"物理真实行情底账文件必须存在: {real_quote_path}")

        with open(real_quote_path, "r", encoding="utf-8") as f:
            raw_quote_data = json.load(f)

        nvda_quote = raw_quote_data["quotes"]["NVDA"]
        self.assertTrue(nvda_quote["is_valid"])
        self.assertEqual(nvda_quote["ticker"], "NVDA")
        real_current_price = float(nvda_quote["current_price"])
        self.assertEqual(real_current_price, 204.64, "真实落盘现价必须精确为 204.64 美元")

        # 将物理介质提取的真实价格注入引擎
        real_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "val_current_price": real_current_price})
        result = self.engine.evaluate_buy_signal(real_facts)

        self.assertEqual(result.ticker, "NVDA")
        self.assertEqual(result.val_current_price, 204.64)
        self.assertEqual(result.status_buy_signal, BuySignalTier.PIVOT_TRIGGERED.value)
        self.assertEqual(result.price_boundaries.val_stop_loss_price, 186.00)
        self.assertEqual(result.price_boundaries.val_breakeven_trigger_price, 242.00)
        self.assertEqual(result.price_boundaries.val_extended_limit_price, 210.00)
        self.assertTrue(result.price_boundaries.is_within_buy_range)

    def test_mathematical_defense_and_finite_liability(self):
        """【UT-SEPA-02: 金融数学边界与有限责任防御 (负价/零价/空序列退化)】

        1. 测试功能与测试点:
           - 验证枢轴买点与当前股价负数、零值异常输入时的物理拦截。
           - 验证当收缩形态列表为空或仅有单笔收缩时，系统优雅退化而不是崩溃或误报。

        2. 正常函数业务边界与参数契约:
           - val_pivot_price 必须 > 0.0。
           - val_current_price 必须 >= 0.0 (有限责任下界)。
           - pct_recent_contractions 至少需要 2 轮收敛方可构成有效 VCP 结构。

        3. 测试数据与模拟场景说明:
           - 场景 1: val_pivot_price = -10.00。
           - 场景 2: val_pivot_price = 0.00。
           - 场景 3: val_current_price = -5.00。
           - 场景 4: pct_recent_contractions = [] (空列表)。
           - 场景 5: pct_recent_contractions = [15.0] (单笔收缩)。

        4. 预期断言与结果验证:
           - 场景 1~3 断言抛出 ValueError 并携带明确中文错误说明。
           - 场景 4 断言 vcp_status == NO_CONTRACTION 且 footprint_code == '0W 0/0 0T'。
           - 场景 5 断言 vcp_status != TIGHT_PIVOT_READY。
        """
        # 1. 负数枢轴买点价格防御
        with self.assertRaises(ValueError) as ctx_neg_pivot:
            self.engine.calculate_sepa_price_boundaries(val_pivot_price=-10.00, val_current_price=100.00)
        self.assertIn("枢轴买点价格必须大于0", str(ctx_neg_pivot.exception))

        # 2. 零价格枢轴买点防御
        with self.assertRaises(ValueError) as ctx_zero_pivot:
            self.engine.calculate_sepa_price_boundaries(val_pivot_price=0.00, val_current_price=100.00)
        self.assertIn("枢轴买点价格必须大于0", str(ctx_zero_pivot.exception))

        # 3. 负数当前股价防御 (有限责任下界)
        with self.assertRaises(ValueError) as ctx_neg_curr:
            self.engine.calculate_sepa_price_boundaries(val_pivot_price=100.00, val_current_price=-5.00)
        self.assertIn("当前股价不可为负", str(ctx_neg_curr.exception))

        # 4. 空收缩序列安全退化测试
        empty_contractions_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "pct_recent_contractions": []})
        vcp_empty = self.engine.diagnose_vcp_pattern(empty_contractions_facts)
        self.assertEqual(vcp_empty["vcp_status"], VcpContractionStatus.NO_CONTRACTION)
        self.assertEqual(vcp_empty["footprint_code"], "0W 0/0 0T")
        self.assertFalse(vcp_empty["is_volume_dryup_confirmed"])

        # 5. 单次收缩无法确立 VCP (至少需要 2T 收敛)
        single_contraction_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "pct_recent_contractions": [15.0]})
        vcp_single = self.engine.diagnose_vcp_pattern(single_contraction_facts)
        self.assertNotEqual(vcp_single["vcp_status"], VcpContractionStatus.TIGHT_PIVOT_READY)

    def test_floating_point_strict_boundaries(self):
        """【UT-SEPA-03: 严格浮点数与美分级临界点测试 (恰好买点/追高边界/RS门槛)】

        1. 测试功能与测试点:
           - 验证现价恰好触碰枢轴买点 (200.00) 时的触发有效性。
           - 验证现价恰好等于追高上限 (210.00) 时的闭区间临界包含。
           - 验证现价高出追高上限 1 美分 (210.01) 时的刚性风控拦截 (EXTENDED_OVERBOUGHT)。
           - 验证相对强度 RS Rank 恰好 70.00 分与 69.90 分的一票否决临界。

        2. 正常函数业务边界与参数契约:
           - 安全买入闭区间: Pivot <= Price <= Pivot * 1.05。
           - 追高拦截: Price > Pivot * 1.05 时必须发出严禁追高指令。
           - 趋势模板第 8 项: RS Rank >= 70.0。

        3. 测试数据与模拟场景说明:
           - 买点 200.00，追高上限 210.00，分别测试 200.00、210.00、210.01 三种价位。
           - 相对强度分别传入 70.00 (刚好达标) 与 69.90 (失格)。

        4. 预期断言与结果验证:
           - 200.00 与 210.00 断言 is_within_buy_range 为 True，状态为 PIVOT_TRIGGERED。
           - 210.01 断言 is_within_buy_range 为 False，状态为 EXTENDED_OVERBOUGHT，提示“严禁追高”。
           - RS 70.00 断言趋势模板通过，RS 69.90 断言趋势模板否决。
        """
        # 1. 现价恰好等于买点 (200.00) -> 属于合法区间内，触发放量突破
        exact_pivot_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "val_current_price": 200.00})
        result_exact_pivot = self.engine.evaluate_buy_signal(exact_pivot_facts)
        self.assertTrue(result_exact_pivot.price_boundaries.is_within_buy_range)
        self.assertEqual(result_exact_pivot.status_buy_signal, BuySignalTier.PIVOT_TRIGGERED.value)

        # 2. 现价恰好等于追高上限 (200.00 * 1.05 = 210.00) -> 仍处于闭区间合法边缘
        exact_limit_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "val_current_price": 210.00})
        result_exact_limit = self.engine.evaluate_buy_signal(exact_limit_facts)
        self.assertTrue(result_exact_limit.price_boundaries.is_within_buy_range)
        self.assertEqual(result_exact_limit.status_buy_signal, BuySignalTier.PIVOT_TRIGGERED.value)

        # 3. 现价高出追高上限 1 美分 (210.01) -> 刚性拦截，触发 EXTENDED_OVERBOUGHT
        over_1cent_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "val_current_price": 210.01})
        result_over_1cent = self.engine.evaluate_buy_signal(over_1cent_facts)
        self.assertFalse(result_over_1cent.price_boundaries.is_within_buy_range)
        self.assertEqual(result_over_1cent.status_buy_signal, BuySignalTier.EXTENDED_OVERBOUGHT.value)
        self.assertIn("严禁追高", result_over_1cent.directive_action_zh)

        # 4. 相对强度 RS 恰好等于 70.00 分门槛 -> 通过第 8 项
        exact_rs_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "num_rs_rank": 70.00})
        trend_exact_rs = self.engine.diagnose_trend_stage(exact_rs_facts)
        self.assertTrue(trend_exact_rs["checks"]["8_rs_rank_above_threshold"])
        self.assertTrue(trend_exact_rs["is_trend_template_passed"])

        # 5. 相对强度 RS 为 69.90 分 -> 一票否决
        under_rs_facts = SepaInputFacts(**{**self.healthy_facts.__dict__, "num_rs_rank": 69.90})
        trend_under_rs = self.engine.diagnose_trend_stage(under_rs_facts)
        self.assertFalse(trend_under_rs["checks"]["8_rs_rank_above_threshold"])
        self.assertFalse(trend_under_rs["is_trend_template_passed"])

    def test_squat_and_reversal_recovery_scenario(self):
        """【UT-SEPA-04: 米奈尔维尼深蹲 (Squat) 战术场景与防误杀保护】

        1. 测试功能与测试点:
           - 验证突破后回踩买点下方的“深蹲 (Squat)”保护算法。
           - 当股价跌破买点但守住刚性止损线 (186.00) 与 50日均线 (185.20)，且成交量处于缩量状态时，系统判定主力未跑路。
           - 避免散户在深蹲洗盘时恐慌割肉。

        2. 正常函数业务边界与参数契约:
           - StopLoss < CurrentPrice < PivotPrice 且 CurrentPrice > MA50 且 Volume < AvgVolume。
           - 状态流转为 SQUAT_REVERSAL_WATCH，置位 is_squat_holding = True。

        3. 测试数据与模拟场景说明:
           - 股价突破 200 后受大盘拖累回落至 196.00，成交量缩至 2800 万股 (均量 3500 万股)。

        4. 预期断言与结果验证:
           - 断言 status_buy_signal 为 SQUAT_REVERSAL_WATCH。
           - 断言 is_squat_holding 为 True。
           - 断言 directive_action_zh 明确包含“深蹲”与“坚决不割肉”。
        """
        # 突破后大盘跳水，股价从 204.64 跌落至 196.00:
        # - 在买点 200.00 下方
        # - 但远高于刚性止损线 186.00
        # - 处于 50日均线 185.20 之上
        # - 成交量缩量至 2800万股 (低于均量 3500万，主力未跑路)
        squat_facts = SepaInputFacts(
            **{
                **self.healthy_facts.__dict__,
                "val_current_price": 196.00,
                "num_current_volume": 28000000.0,
            }
        )
        result_squat = self.engine.evaluate_buy_signal(squat_facts)

        self.assertEqual(result_squat.status_buy_signal, BuySignalTier.SQUAT_REVERSAL_WATCH.value)
        self.assertTrue(result_squat.is_squat_holding, "必须置位深蹲保护标志位")
        self.assertIn("深蹲", result_squat.directive_action_zh)
        self.assertIn("坚决不割肉", result_squat.directive_action_zh)
        self.assertEqual(result_squat.meta_buy_signal["state_id"], "SIG_05")

    def test_price_boundaries_decoupled_calculation(self):
        """【UT-SEPA-05: 价格走廊与风控边界解耦纯计算核验】

        1. 测试功能与测试点:
           - 验证 calculate_sepa_price_boundaries 独立纯计算函数的准确性。
           - 验证买点上浮 5% 追高限、下浮 7% 刚性止损、下浮 5% 建议止损及 3R 目标位完全遵循配置解耦驱动。

        2. 正常函数业务边界与参数契约:
           - 参数字典驱动，严禁代码硬编码魔法值。

        3. 测试数据与模拟场景说明:
           - Pivot=200.00, 现价=204.64，采用标准 7% 硬止损与 5% 追高上限配置。

        4. 预期断言与结果验证:
           - 断言止损线为 186.00，建议止损 190.00，风险单笔 14.00，追高上限 210.00，目标位 242.00。
           - 断言 is_within_buy_range 为 True。
        """
        boundaries = self.engine.calculate_sepa_price_boundaries(
            val_pivot_price=200.00,
            val_current_price=204.64,
            params=self.default_params,
        )
        self.assertEqual(boundaries.val_pivot_price, 200.00)
        self.assertEqual(boundaries.val_stop_loss_price, 186.00)
        self.assertEqual(boundaries.val_recommended_stop_price, 190.00)
        self.assertEqual(boundaries.val_risk_unit_usd, 14.00)
        self.assertEqual(boundaries.val_breakeven_trigger_price, 242.00)
        self.assertEqual(boundaries.val_extended_limit_price, 210.00)
        self.assertEqual(boundaries.val_target_profit_price, 242.00)
        self.assertTrue(boundaries.is_within_buy_range)

    def test_trend_template_eight_criteria_verification(self):
        """【UT-SEPA-06: 趋势模板 8 大硬指标全票通过与一票否决】

        1. 测试功能与测试点:
           - 验证米奈尔维尼第二阶段 (Stage 2 Markup) 8 项硬性趋势指标检验器。
           - 验证全票通过与破坏单项时的一票否决逻辑。

        2. 正常函数业务边界与参数契约:
           - 8项条件: 1.现价>MA150&MA200; 2.MA150>MA200; 3.MA200向上; 4.MA50>MA150&MA200; 5.现价>MA50; 6.现价>52周低点+30%; 7.现价在52周高点-25%内; 8.RS Rank>=70。

        3. 测试数据与模拟场景说明:
           - 样本 A: 8项全满健康标的。
           - 样本 B: 现价跌破 50日线 (破坏第 5 项)。

        4. 预期断言与结果验证:
           - 样本 A 断言 is_trend_template_passed 为 True，阶段为 STAGE_2_MARKUP。
           - 样本 B 断言 is_trend_template_passed 为 False，5_price_above_50d 为 False。
        """
        trend_diag = self.engine.diagnose_trend_stage(self.healthy_facts)
        self.assertTrue(trend_diag["is_trend_template_passed"])
        self.assertEqual(trend_diag["trend_stage"], TrendStageState.STAGE_2_MARKUP)
        self.assertEqual(len(trend_diag["checks"]), 8)
        self.assertTrue(all(trend_diag["checks"].values()))

        # 破坏第 5 项 (股价跌破 50日均线)
        broken_facts_5 = SepaInputFacts(**{**self.healthy_facts.__dict__, "val_current_price": 180.00})
        diag_broken_5 = self.engine.diagnose_trend_stage(broken_facts_5)
        self.assertFalse(diag_broken_5["is_trend_template_passed"])
        self.assertFalse(diag_broken_5["checks"]["5_price_above_50d"])

    def test_ssot_state_registry_completeness(self):
        """【UT-SEPA-07: 单一事实来源 (SSOT) 状态空间元数据完备性】

        1. 测试功能与测试点:
           - 验证 SEPA 状态注册表中关于趋势阶段、VCP 收敛形态、买入信号等全部枚举值的元数据完备性。
           - 确保状态 ID、中文商业直觉与操盘指引文本全量注册，杜绝未定义状态。

        2. 正常函数业务边界与参数契约:
           - 遍历 TrendStageState, VcpContractionStatus, BuySignalTier。

        3. 测试数据与模拟场景说明:
           - 枚举扫描与元数据字典验证。

        4. 预期断言与结果验证:
           - 断言所有注册状态 state_id != 'UNKNOWN'。
           - 断言中文文本长度充实 (>10 字符)。
        """
        for stage in TrendStageState:
            meta = get_sepa_state_metadata("trend_stage", stage)
            self.assertNotEqual(meta["state_id"], "UNKNOWN")
            self.assertTrue(len(meta["business_intuition_zh"]) > 10)
            self.assertTrue(len(meta["action_directive_zh"]) > 5)

        for vcp in VcpContractionStatus:
            meta = get_sepa_state_metadata("vcp_status", vcp)
            self.assertNotEqual(meta["state_id"], "UNKNOWN")

        for sig in BuySignalTier:
            meta = get_sepa_state_metadata("buy_signal", sig)
            self.assertNotEqual(meta["state_id"], "UNKNOWN")
            self.assertTrue(len(meta["business_intuition_zh"]) > 10)

    def test_ut_sepa_08_negative_contraction_abs_cleaning_defense(self):
        """【UT-SEPA-08: VCP 收缩负数输入绝对值清洗与怪异足迹防御断言】

        一、测试功能与测试点:
            验证 VCP 波动收缩形态的负数幅度防御与输入清洗机制:
            当上游或行情接口因异常波动传入负数收缩序列 (例如 [-28.0, 14.0, -6.0, 2.5]) 时，
            引擎必须自动取绝对值清洗，严禁生成如 '8W -28/2.5 4T' 等违背金融常识的怪异足迹。

        二、正常函数业务边界与参数契约:
            - pct_recent_contractions 输入带有负号的波动率。

        三、测试数据与模拟场景说明:
            测试含有负数的 VCP 序列。

        四、预期断言与结果验证:
            断言 footprint_code 绝不包含负号 '-'。
            断言 footprint_code 为 '8W 28/2.5 4T'。
            断言 vcp_status == VcpContractionStatus.TIGHT_PIVOT_READY。
        """
        negative_facts = SepaInputFacts(
            **{
                **self.healthy_facts.__dict__,
                "pct_recent_contractions": [-28.0, 14.0, -6.0, 2.5],
            }
        )
        vcp_res = self.engine.diagnose_vcp_pattern(negative_facts)
        self.assertNotIn("-", vcp_res["footprint_code"], f"足迹不能含负号: {vcp_res['footprint_code']}")
        self.assertIn("28/2.5", vcp_res["footprint_code"])
        self.assertEqual(vcp_res["vcp_status"], VcpContractionStatus.TIGHT_PIVOT_READY)

    def test_ut_sepa_09_zero_volume_division_defense(self):
        """【UT-SEPA-09: 日均成交量为零边界防除零除负防御断言】

        一、测试功能与测试点:
            验证当标的 50日均成交量 num_avg_volume_50d <= 0 (如停牌刚复牌或冷门标的) 时，
            系统通过 ValueError 拒绝缺失的成交量基线。

        二、正常函数业务边界与参数契约:
            - num_avg_volume_50d: 0.0。

        三、测试数据与模拟场景说明:
            测试日均成交量为 0 的极端边界。

        四、预期断言与结果验证:
            断言 evaluate_buy_signal 明确拒绝生成信号。
        """
        zero_vol_facts = SepaInputFacts(
            **{
                **self.healthy_facts.__dict__,
                "num_avg_volume_50d": 0.0,
            }
        )
        with self.assertRaisesRegex(ValueError, "历史日均成交量"):
            self.engine.evaluate_buy_signal(zero_vol_facts)

    def test_ut_sepa_10_buyer_narrative_card_deengineering(self):
        """【UT-SEPA-10: 买方通俗商业直觉全息研报卡片 narrative_zh 去工程符号化断言】

        一、测试功能与测试点:
            验证去工程符号化与买方自然语言输出规范:
            SepaBuySignalResult 必须输出自然流畅、面向买方基金经理的通俗中文研报卡片 (narrative_zh)，
            包含所处阶段、VCP 足迹、击球区间、止损线与靶心，严禁向投资人暴露纯英文代码代号。

        二、正常函数业务边界与参数契约:
            - 正常 Stage 2 突破标的。

        三、测试数据与模拟场景说明:
            测试 NVDA 突破场景研报输出。

        四、预期断言与结果验证:
            断言 narrative_zh 非空且包含 "第二阶段主升突围期"。
            断言 narrative_zh 包含 "黄金击球区间" 与 "风控红线"。
            断言 narrative_zh 包含 "3:1"。
            断言 narrative_zh 严禁包含英文下划线工程状态名。
        """
        res = self.engine.evaluate_buy_signal(self.healthy_facts)
        card = res.narrative_zh
        self.assertTrue(len(card) > 50, "研报卡片文本量必须充实")
        self.assertIn("第二阶段主升突围期", card)
        self.assertIn("黄金击球区间", card)
        self.assertIn("风控红线", card)
        self.assertIn("3:1", card)
        self.assertNotIn("Stage_2_Markup", card)
        self.assertNotIn("Pivot_Triggered", card)

    def test_ut_sepa_11_facade_and_core_ssot_equivalence(self):
        """【UT-SEPA-11: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.sepa_buy_signal_engine` 中继门面与底层核心
            `financial_core.engines.sepa_buy_signal_engine` 计算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准 SEPA 买点评估场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        from finance_tools.sepa_buy_signal_engine import (
            SepaBuySignalEngine as FacadeEngine,
        )
        facade_engine = FacadeEngine(adaptive_params=self.default_params)
        res_core = self.engine.evaluate_buy_signal(self.healthy_facts)
        res_facade = facade_engine.evaluate_buy_signal(self.healthy_facts)

        self.assertEqual(res_core.status_buy_signal, res_facade.status_buy_signal)
        self.assertEqual(res_core.technical_footprint_code, res_facade.technical_footprint_code)
        self.assertEqual(res_core.narrative_zh, res_facade.narrative_zh)
        self.assertEqual(
            res_core.price_boundaries.val_stop_loss_price,
            res_facade.price_boundaries.val_stop_loss_price,
        )

    def test_ut_sepa_12_to_dict_and_chinese_status_names(self):
        """【UT-SEPA-12: SEPA 买入决策与价格走廊 to_dict() 序列化及自然中文命名断言】

        一、测试功能与测试点:
            1. 验证 SepaBuySignalResult 与 SepaPriceBoundaries 具备标准 to_dict() 方法；
            2. 验证序列化字典中健全包含 trend_stage_zh, vcp_contraction_zh, buy_signal_zh 与 narrative_zh；
            3. 验证价格走廊包含格式化的美分级价格字符串 (如 $186.00)。

        二、正常函数业务边界与参数契约:
            - evaluate_buy_signal 返回结果执行 to_dict()。

        三、测试数据与模拟场景说明:
            - 使用 NVDA 突破场景 facts。

        四、预期断言与结果验证:
            - 断言 to_dict() 字典健全且无 TypeError。
            - 断言 trend_stage_zh == "第二阶段主升突围期"。
            - 断言 buy_signal_zh == "枢轴买点立即触发"。
        """
        res = self.engine.evaluate_buy_signal(self.healthy_facts)
        self.assertEqual(res.status_trend_stage_zh, "第二阶段主升突围期")
        self.assertEqual(res.status_buy_signal_zh, "枢轴买点立即触发")
        self.assertIn("地量", res.status_vcp_contraction_zh)

        d = res.to_dict()
        self.assertIn("ticker", d)
        self.assertIn("trend_stage_zh", d)
        self.assertIn("buy_signal_zh", d)
        self.assertIn("price_boundaries", d)
        self.assertIn("hard_stop_loss_price", d["price_boundaries"])
        self.assertIn("$", d["price_boundaries"]["hard_stop_loss_price"])
        self.assertIn("narrative_zh", d)


if __name__ == "__main__":
    unittest.main()
