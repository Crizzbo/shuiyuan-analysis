"""商业品质与微观血肉引擎测试套件 (Business Quality & Domain Flesh Engine Tests).

覆盖范围:
1. 巴菲特所有者收益真实穿透与三态盈利质量状态机检验;
2. 白酒与消费品微观血肉（批价倒挂、渠道库存 3 态空间、统御提价权）精确诊断;
3. 硬科技半导体 DIO 周转激增与大客户单点脆弱两态诊断;
4. 状态空间注册表 (METRICS_STATE_REGISTRY) 单一事实来源完备性与不变量断言;
5. 向下兼容门面与规范化方法调用等价性检验 (零破坏重构).
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.business_quality_and_moat_engine import (
    EarningsQualityVerdict,
    ChannelInventoryStatus,
    PricingPowerVerdict,
    CustomerVulnerabilityStatus,
    TechOperatingHealthStatus,
    METRICS_STATE_REGISTRY,
    get_metric_state_metadata,
    OwnerEarningsInput,
    LiquorConsumerFleshInput,
    TechHardwareFleshInput,
    BusinessQualityAndMoatEngine,
)


class TestBusinessQualityAndMoatEngine(unittest.TestCase):
    """测试商业血肉与品质照妖镜中枢."""

    def setUp(self):
        self.engine = BusinessQualityAndMoatEngine()

    def test_owner_earnings_buffett_filter(self):
        """【UT-QUALITY-01: 巴菲特所有者收益真实穿透与三态盈利质量状态机检验】

        1. 测试功能与测试点:
           - 验证 calculate_buffett_owner_earnings 巴菲特所有者收益真实造血能力穿透。
           - 所有者收益公式: Owner Earnings = Net Income + D&A - Maintenance CapEx - SBC - ΔWorking Capital。
           - 剥离虚假繁荣: 穿透股权激励 (SBC 发股票发工资) 与营运资本恶化对净利润的侵蚀。
           - 盈利质量三态判定: HIGH_QUALITY (>=0.85)、MODERATE_HAIRCUT (0.50~0.85)、SEVERE_HAIRCUT (<0.50)。

        2. 正常函数业务边界与参数契约:
           - 输入为 OwnerEarningsInput 强类型对象。
           - earnings_quality_ratio = Owner Earnings / Reported Net Income。

        3. 测试数据与模拟场景说明:
           - 场景 1 (严重虚胖): 净利润 1 亿，D&A 2000 万，资本开支 5000 万 (80% 为维持性开支 4000 万)，SBC 高达 4500 万，应收增加占用 1500 万。真实造血仅 2000 万 (占比 20%)。
           - 场景 2 (高质量造血): 净利润 1 亿，D&A 1000 万，维护性开支仅 600 万，无 SBC 与营运资本占用，实际造血 1.04 亿 (占比 104%)。

        4. 预期断言与结果验证:
           - 场景 1 断言 owner_earnings == 20M, quality_ratio == 0.20，verdict 为 SEVERE_HAIRCUT，state_id 为 'EQ_03'，严重度为 5 级。
           - 场景 2 断言 owner_earnings == 104M，verdict 为 HIGH_QUALITY，严重度为 1 级。
        """
        # 1. 虚胖企业案例: 1亿利润，维护开支 4000 万，SBC 4500 万，营运资本占用 1500 万 -> 实际造血仅 2000 万 (20%)
        params_severe = OwnerEarningsInput(
            reported_net_income=100_000_000,
            depreciation_amortization=20_000_000,
            total_capex=50_000_000,
            maintenance_capex_ratio=0.80,  # 4000 万维护性开支
            stock_based_compensation=45_000_000,  # 高达 4500 万发股票发工资
            working_capital_change=15_000_000,  # 应收账款增加占用 1500 万
            shares_outstanding=50_000_000,
        )
        res_severe = self.engine.calculate_buffett_owner_earnings(params_severe)
        self.assertEqual(res_severe["owner_earnings"], 20_000_000)
        self.assertEqual(res_severe["earnings_quality_ratio"], 0.20)
        self.assertEqual(res_severe["earnings_quality_verdict"], EarningsQualityVerdict.SEVERE_HAIRCUT.value)
        self.assertEqual(res_severe["earnings_quality_enum"], EarningsQualityVerdict.SEVERE_HAIRCUT)

        # 校验状态元数据与投资动作指令
        meta = res_severe["state_metadata"]
        self.assertEqual(meta["state_id"], "EQ_03")
        self.assertEqual(meta["severity_level"], 5)
        self.assertIn("虚胖", meta["business_intuition_zh"])
        self.assertIn("下调买入击球区", meta["action_directive_zh"])

        # 2. 高质量造血企业案例: 1亿利润，D&A 1000 万，资本开支仅 1000 万 (维护开支 600 万)，无 SBC
        params_high = OwnerEarningsInput(
            reported_net_income=100_000_000,
            depreciation_amortization=10_000_000,
            total_capex=10_000_000,
            maintenance_capex_ratio=0.60,
            stock_based_compensation=0.0,
            working_capital_change=0.0,
            shares_outstanding=50_000_000,
        )
        res_high = self.engine.calculate_buffett_owner_earnings(params_high)
        # 100M + 10M - 6M = 104M -> quality_ratio = 1.04 >= 0.85
        self.assertEqual(res_high["owner_earnings"], 104_000_000)
        self.assertEqual(res_high["earnings_quality_verdict"], EarningsQualityVerdict.HIGH_QUALITY.value)
        self.assertEqual(res_high["state_metadata"]["severity_level"], 1)

    def test_liquor_wuliangye_flesh_diagnostics(self):
        """【UT-QUALITY-02: 白酒与消费品微观血肉（批价倒挂/渠道库存/统御提价权）精确诊断】

        1. 测试功能与测试点:
           - 验证 diagnose_liquor_channel_flesh 消费品特异性微观血肉解剖能力。
           - 渠道批价倒挂识别: 终端批发价 < 出厂结算价，利差为负。
           - 渠道商打款意愿枯竭: 资产负债表合同负债 (预收账款) 出现负增长。
           - 渠道库存三态状态机: HEALTHY_LIQUID (<2.5m)、ELEVATED_OVERHANG (2.5m~4.0m 悬顶堰塞湖)、CRITICAL_CLOG (>=4.0m 极危阻塞)。

        2. 正常函数业务边界与参数契约:
           - 输入为 LiquorConsumerFleshInput。
           - 倒挂差额 = Wholesale - Factory。

        3. 测试数据与模拟场景说明:
           - 样本 A (典型五粮液普五倒挂行情): 出厂价 1019 元，一批价 930 元 (倒挂 -89 元)，合同负债从 100 亿跌至 75 亿 (-25%)，库存 3.2 个月。
           - 样本 B (极端渠道堰塞湖): 库存高达 4.5 个月，批价严重倒挂 -200 元。

        4. 预期断言与结果验证:
           - 样本 A 断言 price_inversion_active 为 True，倒挂价差为 -89.0 元，channel_inventory_status 为 ELEVATED_OVERHANG，定价权得分 < 50。
           - 样本 B 断言 channel_inventory_status 为 CRITICAL_CLOG，严重度等级为 5，动作指令包含“一票否决”。
        """
        # 出厂价 1019, 批价 930, 渠道库存 3.2 个月, 合同负债从 100 亿跌到 75 亿 (-25%)
        params = LiquorConsumerFleshInput(
            factory_price=1019.0,
            wholesale_market_price=930.0,
            current_contract_liabilities=7_500_000_000,
            prior_contract_liabilities=10_000_000_000,
            channel_inventory_months=3.2,
            gross_margin=0.75,
        )
        res = self.engine.diagnose_liquor_channel_flesh(params)
        self.assertTrue(res["price_inversion_active"])
        self.assertEqual(res["inversion_spread_yuan"], -89.0)
        self.assertLess(res["inversion_ratio_pct"], -8.0)
        self.assertTrue(res["dealers_confidence_drain"])
        self.assertEqual(res["channel_inventory_status"], ChannelInventoryStatus.ELEVATED_OVERHANG.value)
        self.assertEqual(res["channel_inventory_enum"], ChannelInventoryStatus.ELEVATED_OVERHANG)
        self.assertEqual(res["channel_inventory_metadata"]["state_id"], "CI_02")
        self.assertLess(res["pricing_power_score"], 50.0)

        # 测试极端堰塞湖情况 (库存 >= 4.0 个月)
        params_clog = LiquorConsumerFleshInput(
            factory_price=1000.0,
            wholesale_market_price=800.0,
            current_contract_liabilities=50.0,
            prior_contract_liabilities=100.0,
            channel_inventory_months=4.5,
            gross_margin=0.60,
        )
        res_clog = self.engine.diagnose_liquor_channel_flesh(params_clog)
        self.assertEqual(res_clog["channel_inventory_status"], ChannelInventoryStatus.CRITICAL_CLOG.value)
        self.assertEqual(res_clog["channel_inventory_metadata"]["severity_level"], 5)
        self.assertIn("一票否决", res_clog["channel_inventory_metadata"]["action_directive_zh"])

    def test_tech_dio_and_concentration_risk(self):
        """【UT-QUALITY-03: 硬科技半导体存货周转天数(DIO)激增与大客户单点脆弱两态诊断】

        1. 测试功能与测试点:
           - 验证 diagnose_tech_inventory_cycle_and_moat 半导体硬科技专属诊断。
           - 存货周期周转天数 (DIO) 激增告警: 连续季度 DIO 激增超过 20 天，预示行业下行周期或滞销。
           - 大客户单点脆弱性 (Customer Vulnerability): 前五大客户收入占比 > 60% 判定为高脆弱 (HIGH_DEPENDENCY)。
           - 研发费用激进资本化粉饰识别: 资本化率超过 15% 触发会计真实性预警。

        2. 正常函数业务边界与参数契约:
           - 输入为 TechHardwareFleshInput。
           - 综合健康度输出 TechOperatingHealthStatus 枚举。

        3. 测试数据与模拟场景说明:
           - 当前 DIO 135 天，较上季度 105 天暴增 30 天；前五大客户占比高达 72%；研发资本化率达 18%。

        4. 预期断言与结果验证:
           - 断言 inventory_cycle_warning 为 True。
           - 断言 customer_vulnerability 为 HIGH_DEPENDENCY。
           - 断言 rd_capitalization_warning 为 True。
           - 断言 tech_operating_health 为 FRAGILE_DOWNCYCLE，严重度等级为 5，动作指令包含“立刻防守”。
        """
        params = TechHardwareFleshInput(
            current_dio_days=135.0,
            prior_dio_days=105.0,  # DIO 单季度激增 30 天
            top_5_customer_revenue_share=0.72,  # 前五大客户占 72%
            datacenter_or_core_segment_share=0.85,
            capitalized_rd_ratio=0.18,  # 研发资本化 18% 存在粉饰嫌疑
        )
        res = self.engine.diagnose_tech_inventory_cycle_and_moat(params)
        self.assertTrue(res["inventory_cycle_warning"])
        self.assertEqual(res["customer_vulnerability"], CustomerVulnerabilityStatus.HIGH_DEPENDENCY.value)
        self.assertEqual(res["customer_vulnerability_enum"], CustomerVulnerabilityStatus.HIGH_DEPENDENCY)
        self.assertTrue(res["rd_capitalization_warning"])
        self.assertEqual(res["tech_operating_health"], TechOperatingHealthStatus.FRAGILE_DOWNCYCLE.value)
        self.assertEqual(res["tech_operating_health_enum"], TechOperatingHealthStatus.FRAGILE_DOWNCYCLE)

        # 校验硬科技健康度元数据
        meta_health = res["tech_operating_health_metadata"]
        self.assertEqual(meta_health["severity_level"], 5)
        self.assertIn("立刻防守", meta_health["action_directive_zh"])

    def test_state_registry_ssot_completeness(self):
        """【UT-QUALITY-04: 商业品质状态空间注册表 (METRICS_STATE_REGISTRY) 单一事实来源完备性与不变量断言】

        1. 测试功能与测试点:
           - 验证五大商业品质领域的全局元数据注册表完备性。
           - 领域涵盖: 盈利质量 (earnings_quality)、渠道库存 (channel_inventory)、定价权 (pricing_power)、客户脆弱性 (customer_vulnerability)、硬科技经营健康度 (tech_operating_health)。
           - 不变量校验: 每个状态必须包含 state_id, state_name, numerical_interval, severity_level, business_intuition_zh, action_directive_zh。
           - 严重度约束: 严格介于 1 (优异安全) 至 5 (极度危殆) 之间。

        2. 正常函数业务边界与参数契约:
           - 遍历 METRICS_STATE_REGISTRY 全量结构。

        3. 测试数据与模拟场景说明:
           - 字典反射遍历与断言。

        4. 预期断言与结果验证:
           - 断言 5 大领域全部注册。
           - 断言必填字段子集验证全票通过。
           - 断言 severity_level 为 1~5 的整数。
           - 断言中文解读与投资动作指令非空且具有足够长度。
        """
        domains = [
            "earnings_quality",
            "channel_inventory",
            "pricing_power",
            "customer_vulnerability",
            "tech_operating_health",
        ]
        required_meta_keys = {
            "state_id",
            "state_name",
            "numerical_interval",
            "severity_level",
            "business_intuition_zh",
            "action_directive_zh",
        }

        for domain in domains:
            self.assertIn(domain, METRICS_STATE_REGISTRY, f"注册表必须包含 {domain} 领域")
            states = METRICS_STATE_REGISTRY[domain]
            self.assertGreaterEqual(len(states), 2, f"{domain} 至少具备 2 个以上状态空间")

            for state_val, meta in states.items():
                self.assertTrue(required_meta_keys.issubset(set(meta.keys())), f"状态 {state_val} 缺少必填字段")
                self.assertIsInstance(meta["severity_level"], int)
                self.assertTrue(1 <= meta["severity_level"] <= 5, "严重度等级必须在 1~5 之间")
                self.assertGreater(len(meta["business_intuition_zh"]), 5, "商业直觉解读不能过于简陋")
                self.assertGreater(len(meta["action_directive_zh"]), 5, "投资动作指令不能过于简陋")

    def test_backward_compatibility_facade(self):
        """【IT-QUALITY-05: 商业品质引擎向下兼容门面与规范化方法调用等价性检验】

        1. 测试功能与测试点:
           - 验证 BusinessQualityAndMoatEngine 的向下兼容门面。
           - 确保 calculate_buffett_owner_earnings 与 compute_owner_earnings 返回 100% 物理等价。
           - 确保 diagnose_liquor_channel_flesh 与 evaluate_liquor_flesh 返回 100% 物理等价。
           - 保证重构过程中不破坏老脚本或上层报表调用。

        2. 正常函数业务边界与参数契约:
           - 新旧方法传入相同参数，返回字典逐键逐值完全一致。

        3. 测试数据与模拟场景说明:
           - 构造标准所有者收益与白酒微观血肉输入事实。

        4. 预期断言与结果验证:
           - 断言 res_new == res_old。
           - 断言 res_liq_new == res_liq_old。
        """
        params_oe = OwnerEarningsInput(
            reported_net_income=50_000_000,
            depreciation_amortization=5_000_000,
            total_capex=10_000_000,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=2_000_000,
            working_capital_change=1_000_000,
            shares_outstanding=10_000_000,
        )
        res_new = self.engine.calculate_buffett_owner_earnings(params_oe)
        res_old = self.engine.compute_owner_earnings(params_oe)
        self.assertEqual(res_new, res_old, "新旧巴菲特所有者收益计算输出必须完全一致")

        params_liq = LiquorConsumerFleshInput(
            factory_price=1000.0,
            wholesale_market_price=1100.0,
            current_contract_liabilities=100.0,
            prior_contract_liabilities=90.0,
            channel_inventory_months=2.0,
            gross_margin=0.80,
        )
        res_liq_new = self.engine.diagnose_liquor_channel_flesh(params_liq)
        res_liq_old = self.engine.evaluate_liquor_flesh(params_liq)
        self.assertEqual(res_liq_new, res_liq_old, "新旧白酒微观血肉诊断输出必须完全一致")

    def test_zero_factory_price_division_defense(self):
        """【UT-QUALITY-06: 出厂价为零或极小极端边界下除零下界防御检验】

        1. 测试功能与测试点:
           - 验证当白酒或消费品出厂价 factory_price <= 0 或逼近 0 时，引擎不触发 ZeroDivisionError。
           - 验证 safe_factory_price = max(0.01, float(params.factory_price)) 金融工程下界保护生效。
           - 保证在异常数据输入下系统稳健返回结构化定性状态，杜绝未捕获异常穿透崩溃。

        2. 正常函数业务边界与参数契约:
           - factory_price 通常为大于零的出厂价格。
           - 当输入 0.0 时，触发底层防除零下界保护。

        3. 测试数据与模拟场景说明:
           - 传入 factory_price = 0.0, wholesale_market_price = 50.0 极端异常样本。

        4. 预期断言与结果验证:
           - 断言函数正常执行完毕且无除零异常。
           - 断言 price_inversion_active 为 False。
           - 断言 pricing_power_score 数值有限且在合理定义域内。
        """
        params_zero = LiquorConsumerFleshInput(
            factory_price=0.0,
            wholesale_market_price=50.0,
            current_contract_liabilities=10.0,
            prior_contract_liabilities=10.0,
            channel_inventory_months=2.0,
            gross_margin=0.50,
        )
        res = self.engine.diagnose_liquor_channel_flesh(params_zero)
        self.assertFalse(res["price_inversion_active"])
        self.assertIsInstance(res["pricing_power_score"], float)
        self.assertGreaterEqual(res["pricing_power_score"], 0.0)

    def test_ut_quality_07_price_inversion_penalty_and_destruction_verdict(self):
        """【UT-QUALITY-07: 价格严重倒挂下提价权惩罚与价格破坏状态机判定断言】

        一、测试功能与测试点:
            验证提价权评分分支逻辑短路缺陷修复:
            旧代码中当渠道库存较短 (<= 3.0 个月) 但批发价已发生严重倒挂时，
            被硬编码为 45.0 分，导致漏报严重价格破坏风险。
            重构后系统根据倒挂幅度施加刚性扣分惩罚，准确触发
            SEVERE_PRICE_DESTRUCTION (价格严重倒挂与破坏，< 40 分) 警报。

        二、正常函数业务边界与参数契约:
            - 出厂价 1000 元，场外一批价 700 元 (倒挂 -30%)
            - 渠道库存 2.5 个月 (虽然 <= 3.0 月，但价格体系已经崩塌)

        三、测试数据与模拟场景说明:
            测试次高端白酒或热门消费品被黄牛低价抛售、批价击穿出厂线的场景。

        四、预期断言与结果验证:
            断言 price_inversion_active == True。
            断言 pricing_power_score < 40.0 (触发价格破坏区间)。
            断言 pricing_power_verdict == PricingPowerVerdict.SEVERE_PRICE_DESTRUCTION.value。
            断言 pricing_power_metadata["severity_level"] == 5。
        """
        params = LiquorConsumerFleshInput(
            factory_price=1000.0,
            wholesale_market_price=700.0,  # 严重倒挂 -30%
            current_contract_liabilities=50.0,
            prior_contract_liabilities=100.0,
            channel_inventory_months=2.5,  # 库存虽暂未堰塞，但批价已崩
            gross_margin=0.65,
        )
        res = self.engine.diagnose_liquor_channel_flesh(params)
        self.assertTrue(res["price_inversion_active"])
        self.assertLess(res["pricing_power_score"], 40.0)
        self.assertEqual(
            res["pricing_power_verdict"],
            PricingPowerVerdict.SEVERE_PRICE_DESTRUCTION.value,
        )
        self.assertEqual(
            res["pricing_power_enum"],
            PricingPowerVerdict.SEVERE_PRICE_DESTRUCTION,
        )
        self.assertEqual(res["pricing_power_metadata"]["severity_level"], 5)

    def test_ut_quality_08_reported_loss_and_cash_bleed_warning(self):
        """【UT-QUALITY-08: 账面净利润亏损且所有者现金流失血双重恶化文字警告断言】

        一、测试功能与测试点:
            验证巴菲特所有者收益在双重亏损状态下的文字诊断精确性：
            当财报净利润为负且所有者收益亦为深度失血时，
            系统必须准确输出“账面亏损且真实所有者现金流失血持续恶化”，
            消除针对盈利粉饰的文字不匹配语病。

        二、正常函数业务边界与参数契约:
            - reported_net_income: -50M
            - owner_earnings: 亦为深度负值

        三、测试数据与模拟场景说明:
            测试未盈利科技成长股或重资产周期股下行深渊场景。

        四、预期断言与结果验证:
            断言 warning 字段包含 "账面亏损且真实所有者现金流失血持续恶化"。
            断言 earnings_quality_verdict 为 SEVERE_HAIRCUT。
        """
        params_loss = OwnerEarningsInput(
            reported_net_income=-50_000_000.0,
            depreciation_amortization=5_000_000.0,
            total_capex=20_000_000.0,
            maintenance_capex_ratio=0.80,  # 维护性开支 16M
            stock_based_compensation=10_000_000.0,
            working_capital_change=5_000_000.0,
            shares_outstanding=10_000_000.0,
        )
        res_loss = self.engine.calculate_buffett_owner_earnings(params_loss)
        self.assertLess(res_loss["owner_earnings"], 0.0)
        self.assertIn("账面亏损且真实所有者现金流失血持续恶化", res_loss["warning"])
        self.assertEqual(
            res_loss["earnings_quality_verdict"],
            EarningsQualityVerdict.SEVERE_HAIRCUT.value,
        )

    def test_ut_quality_09_facade_and_core_ssot_equivalence(self):
        """【UT-QUALITY-09: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.business_quality_and_moat_engine` 中继门面与底层核心
            `financial_core.engines.business_quality_and_moat_engine` 输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准商业品质解剖场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        from financial_core.engines.business_quality_and_moat_engine import (
            BusinessQualityAndMoatEngine as CoreEngine,
            LiquorConsumerFleshInput as CoreLiquorInput,
        )
        c_core = CoreLiquorInput(1000.0, 950.0, 80.0, 100.0, 3.1, 0.75)
        c_facade = LiquorConsumerFleshInput(1000.0, 950.0, 80.0, 100.0, 3.1, 0.75)

        core_engine = CoreEngine()
        res_core = core_engine.diagnose_liquor_channel_flesh(c_core)
        res_facade = self.engine.diagnose_liquor_channel_flesh(c_facade)

        self.assertEqual(res_core["pricing_power_score"], res_facade["pricing_power_score"])
        self.assertEqual(res_core["pricing_power_verdict"], res_facade["pricing_power_verdict"])
        self.assertEqual(res_core["channel_inventory_status"], res_facade["channel_inventory_status"])

    def test_ut_quality_10_deengineered_chinese_semantics_and_narrative_zh(self):
        """【UT-QUALITY-10: 商业品质与微观血肉自然中文语义映射与全息研报卡片契约】

        一、测试功能与测试点:
            1. 验证三大诊断函数输出均提供自然中文语义定性：
               - `earnings_quality_verdict_zh`
               - `channel_inventory_status_zh` 与 `pricing_power_verdict_zh`
               - `customer_vulnerability_zh` 与 `tech_operating_health_zh`
            2. 验证三大诊断函数均输出标准 `narrative_zh` 买方全息研报卡片，杜绝工程代号裸露。

        二、正常函数业务边界与参数契约:
            - 所有诊断字典包含 `narrative_zh` 且非空。
            - 包含自然中文研判，如“高质量盈利”、“渠道周转健康”、“统御级提价权”。

        三、测试数据与模拟场景说明:
            测试标准健康消费与硬科技企业数据。

        四、预期断言与结果验证:
            断言 narrative_zh 与 _zh 字段符合中文商业直觉规范。
        """
        # 1. 盈利质量
        oe_p = OwnerEarningsInput(100.0, 10.0, 10.0, 0.60, 0.0, 0.0, 50.0)
        res_oe = self.engine.calculate_buffett_owner_earnings(oe_p)
        self.assertIn("narrative_zh", res_oe)
        self.assertEqual(res_oe["earnings_quality_verdict_zh"], "高质量盈利")
        self.assertIn("【巴菲特所有者收益与真实造血品质研报】", res_oe["narrative_zh"])

        # 2. 消费微观血肉
        liq_p = LiquorConsumerFleshInput(1000.0, 1100.0, 100.0, 90.0, 2.0, 0.80)
        res_liq = self.engine.diagnose_liquor_channel_flesh(liq_p)
        self.assertIn("narrative_zh", res_liq)
        self.assertEqual(res_liq["channel_inventory_status_zh"], "渠道周转健康")
        self.assertEqual(res_liq["pricing_power_verdict_zh"], "统御级提价权")
        self.assertIn("【渠道批价与微观血肉诊断全息研报】", res_liq["narrative_zh"])

        # 3. 硬科技微观血肉
        tech_p = TechHardwareFleshInput(90.0, 90.0, 0.40, 0.80, 0.05)
        res_tech = self.engine.diagnose_tech_inventory_cycle_and_moat(tech_p)
        self.assertIn("narrative_zh", res_tech)
        self.assertEqual(res_tech["customer_vulnerability_zh"], "客户群体多元分散")
        self.assertEqual(res_tech["tech_operating_health_zh"], "科技经营周期稳健")
        self.assertIn("【硬科技存货周期与客户护城河全息研报】", res_tech["narrative_zh"])

    def test_ut_quality_11_business_model_moat_diagnosis_via_knowledge_repository(self):
        """【UT-QUALITY-11: 商业模式法定指标契约与买方护城河全息诊断断言 (配置驱动)】

        一、测试功能与测试点:
            1. 验证 BusinessQualityAndMoatEngine.diagnose_business_model_and_moat 能够
               通过统一知识库加载中枢 KnowledgeRepository 动态加载商业模式契约；
            2. 验证法定指标完备齐备时覆盖率达到 100.0%，研报呈现积极定性；
            3. 验证部分缺失指标时准确计算缺失列表；
            4. 验证未注册商业模式时的优雅安全防御。

        二、正常函数业务边界与参数契约:
            - ticker: "BLK", business_model_id: "asset_management_fee"
            - 传入符合 metrics/catalog.json 的实测指标。

        三、预期断言与结果验证:
            断言 is_registered_model 为 True，metric_coverage_pct == 100.0，
            narrative_zh 包含 "商业模式与护城河全息诊断研报" 与 "资产管理收费"。
        """
        # 场景 A: 资产管理龙头指标全量齐备
        full_metrics = {
            "revenue_growth": 0.12,
            "operating_margin": 0.38,
            "fcf": 4500.0,
        }
        res_full = self.engine.diagnose_business_model_and_moat(
            ticker="BLK",
            business_model_id="asset_management_fee",
            reported_metrics=full_metrics,
        )
        self.assertTrue(res_full["is_registered_model"])
        self.assertEqual(res_full["business_model_id"], "asset_management_fee")
        self.assertEqual(res_full["model_name_zh"], "资产管理收费")
        self.assertEqual(res_full["metric_coverage_pct"], 100.0)
        self.assertEqual(len(res_full["missing_metric_ids"]), 0)
        self.assertTrue(res_full["has_deep_research_markdown"])
        self.assertIn("法定指标完备齐备", res_full["narrative_zh"])
        self.assertIn("【标的 BLK 商业模式与护城河全息诊断研报】", res_full["narrative_zh"])

        # 场景 B: 指标部分缺失
        partial_metrics = {
            "fcf": 3000.0,
        }
        res_partial = self.engine.diagnose_business_model_and_moat(
            ticker="PARTIAL_AM",
            business_model_id="asset_management_fee",
            reported_metrics=partial_metrics,
        )
        self.assertEqual(res_partial["covered_metric_count"], 1)
        self.assertIn("revenue_growth", res_partial["missing_metric_ids"])
        self.assertIn("operating_margin", res_partial["missing_metric_ids"])
        self.assertAlmostEqual(res_partial["metric_coverage_pct"], 33.3, places=1)

        # 场景 C: 未注册模式防御
        res_unknown = self.engine.diagnose_business_model_and_moat(
            ticker="UNKNOWN_CORP",
            business_model_id="non_existent_model",
        )
        self.assertFalse(res_unknown["is_registered_model"])
        self.assertIn("未在知识库底账中检索到模式", res_unknown["narrative_zh"])


if __name__ == "__main__":
    unittest.main()
