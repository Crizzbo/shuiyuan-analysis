"""Canyon 统一单向线性流水线 (Canyon Linear One-Pipeline Architecture).

消除多层包装与中间中继层，提供单一事实来源（SSOT）的 6 大标准作业工位单向流动架构：
  Station 1: 行情新鲜度与时段感知门禁 (QuoteFreshnessGate)
  Station 2: 官方三表刚性平账自检门禁 (OfficialFilingGate)
  Station 3: 宏观压力分与动态弹性安全边际 (MacroElasticMarginEngine)
  Station 4: 自由现金流折现三情景估值走廊 (ThreeScenarioValuation)
  Station 5: 黄金击球买入底线与凯利仓位控制 (GoldenStrikeZoneGate)
  Station 6: 买方投资直觉决策卡与不可篡改时间链条 (DecisionCardAndLedger)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Dict, Any, List, Optional

from ..engines.prediction_ledger import PredictionLedger, HistoricalPredictionSnapshot
from ..engines.macro_shock_transmission_engine import MacroShockTransmissionEngine, MacroShockInput
from ..engines.volatility_surface_engine import VolatilitySurfaceGreeksEngine
from ..engines.quote_freshness_gateway import QuoteFreshnessGateway


class QuoteFreshnessError(ValueError):
    """行情失效或未经新鲜度核验阻断异常。"""
    pass


class BalanceSheetInvariantError(ValueError):
    """官方资产负债表刚性平账方程失衡异常。"""
    pass


@dataclass
class CanyonStationInput:
    """Canyon 单向线性流水线标准化统一输入底账。"""
    ticker: str
    company_name: str
    market: str = "US"                           # "US", "JP", "CN"
    sector: str = "General"                      # 行业分类
    asset_type: str = "EQUITY"                   # "EQUITY", "ETF", "COMMODITY_GOLD"

    # 1. 实时行情与新鲜度核验底账
    current_price: float = 0.0
    quote_timestamp: str = ""                    # 精确到分钟与时区 (如 "2026-10-14 15:45:00 EDT")
    market_session: str = "regular_trading"      # "regular_trading", "pre_market", "after_hours", "closed"
    baseline_reference_price: float = 0.0

    # 2. 官方经审计财报底账 (SEC 10-K/Q 或 JPX 决算短信)
    reported_cash: float = 0.0
    restricted_cash: float = 0.0
    debt_covenant_min_cash: float = 0.0
    total_debt: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    stockholders_equity: float = 0.0
    reported_operating_cash_flow: float = 0.0
    reported_capex: float = 0.0
    maintenance_capex_ratio: float = 0.70
    stock_based_compensation: float = 0.0
    reported_revenue: float = 0.0
    reported_operating_income: float = 0.0
    reported_net_income: float = 0.0
    shares_outstanding: float = 1.0

    # 多资产多态插槽扩展参数 (ETF 与大宗商品)
    etf_expense_ratio: float = 0.0               # ETF 管理费率 (如 0.0003 = 0.03%)
    etf_aum_billion: float = 0.0                 # ETF 资产规模 (十亿美元)
    etf_top10_weight_pct: float = 0.0            # ETF 前十大持仓权重占比 (如 32.5 = 32.5%)
    etf_underlying_nav: float = 0.0              # ETF 底层每股净资产净值 (NAV)
    etf_tracking_error_pct: float = 0.0          # ETF 年化跟踪误差

    gold_tips_10y_real_yield: float = 0.0        # 10年期 TIPS 实际利率 (如 0.018 = 1.8%)
    gold_breakeven_inflation: float = 0.0        # 通胀预期平衡率 (如 0.023 = 2.3%)
    gold_central_bank_net_tonnes: float = 0.0    # 全球主权央行净购金量 (吨)
    gold_physical_premium_pct: float = 0.0       # 交易所实物溢价率 (如 0.02 = 2.0%)
    gold_traditional_anchor_price: float = 0.0   # 传统宏观实际利率锚点基准价

    # 3. 宏观流动性与利率基准
    us_10y_yield: float = 0.044                  # 10年期美债收益率
    vix_index: float = 20.0                      # 市场恐慌指数 VIX
    fed_liquidity_drain_billion: float = 50.0    # 美联储净流动性紧缩规模 (十亿美元)
    company_beta: float = 1.10                   # 权益 Beta

    # 4. 衍生品期权与微观筹码 (可选)
    option_target_strike: float = 0.0
    option_expiry_days: float = 30.0
    option_implied_vol: float = 0.35
    is_call_option: bool = True
    short_interest_pct: float = 0.0


@dataclass
class CanyonDecisionCard:
    """买方机构自然商业投资直觉决策卡 (去工程符号化)。"""
    ticker: str
    company_name: str
    market: str
    quote_timestamp: str
    market_session_state: str
    current_price: float
    asset_type: str
    asset_class_label: str

    # 估值中枢与黄金击球区
    neutral_fair_value: float
    strike_price: float
    elastic_mos_pct: float
    zone_status: str                             # "GOLDEN_STRIKE_ZONE", "NEUTRAL_HOLD", "PREMIUM_OVERVALUED"
    recommended_action: str                      # 自然语言买方投资决策研判
    kelly_position_pct: float                    # 推荐动态仓位配置比例 (半凯利)

    # 三情景估值走廊与催化诱因
    pessimistic_floor: float
    pessimistic_event: str
    optimistic_target: float
    optimistic_event: str

    # 宏观与期权风险洞察
    macro_stress_score: float                    # 宏观综合压力分 (0.0~1.0)
    liquidity_atm_warning: bool                  # 优质蓝筹流动性提款机抛售风险
    options_timing_verdict: str                  # 期权时间衰减与结构评语

    # 密码学不可篡改审计指纹
    ledger_hash: str                             # SHA-256 区块链时间链条指纹
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CanyonLinearPipeline:
    """Canyon 单向线性 6 工位主控制器。"""

    def __init__(self, ledger: Optional[PredictionLedger] = None):
        self.ledger = ledger or PredictionLedger()
        self.macro_engine = MacroShockTransmissionEngine()
        self.volatility_engine = VolatilitySurfaceGreeksEngine()

    # -------------------------------------------------------------
    # 工位 1: 行情新鲜度与时段感知门禁 (QuoteFreshnessGate)
    # -------------------------------------------------------------
    def station_1_quote_freshness(self, inp: CanyonStationInput) -> Dict[str, Any]:
        """核验报价合法性、时间戳新鲜度与市场交易时段状态。"""
        if inp.current_price <= 0.0 or not math.isfinite(inp.current_price):
            raise QuoteFreshnessError(
                f"【工位 1 阻断】标的 {inp.ticker} 最新报价非法 (${inp.current_price:.2f})，价格必须严格大于零有限数值。"
            )

        if not inp.quote_timestamp:
            raise QuoteFreshnessError(
                f"【工位 1 阻断】标的 {inp.ticker} 缺失精确报价时间戳，严禁使用未校准时钟的行情开展投研。"
            )

        # 调用权威行情门禁网关进行时效性与交易时段核验
        currency = "JPY" if inp.market == "JP" else "USD"
        try:
            v_res = QuoteFreshnessGateway.verify_quote(
                price=inp.current_price,
                currency=currency,
                quote_timestamp=inp.quote_timestamp,
                market=inp.market,
            )
        except Exception as e:
            raise QuoteFreshnessError(f"【工位 1 阻断】时间戳或价格解析异常: {e}")

        if not v_res.is_valid:
            raise QuoteFreshnessError(
                f"【工位 1 阻断】标的 {inp.ticker} 行情时效核验未通过: {v_res.message}"
            )

        # 检查是否以陈旧历史行情冒充盘中实时交易
        raw_session = (inp.market_session or "").lower().strip()
        intraday_sessions = {"regular_trading", "pre_market", "after_hours"}
        if raw_session in intraday_sessions and not v_res.is_fresh_today:
            raise QuoteFreshnessError(
                f"【工位 1 阻断】标的 {inp.ticker} 报价并非当前交易日产生 (滞后 {v_res.age_hours:.1f}h)，"
                f"严禁按输入的盘中标记 '{raw_session}' 冒充实时市价！"
            )

        session = v_res.session_status
        is_intraday = session in intraday_sessions
        session_label = v_res.formatted_label

        return {
            "status": "PASSED",
            "current_price": inp.current_price,
            "quote_timestamp": inp.quote_timestamp,
            "market_session": session,
            "session_label": session_label,
            "is_intraday": is_intraday,
        }

    # -------------------------------------------------------------
    # 工位 2: 官方三表刚性平账自检门禁 (OfficialFilingGate)
    # -------------------------------------------------------------
    def station_2_official_filing(self, inp: CanyonStationInput) -> Dict[str, Any]:
        """执行官方三表刚性平账方程自检或多资产合规核验。"""
        asset_type = (inp.asset_type or "EQUITY").upper().strip()

        if asset_type == "ETF":
            # ETF 基础合规核验
            nav = inp.etf_underlying_nav if inp.etf_underlying_nav > 0.0 else inp.current_price
            if inp.etf_expense_ratio < 0.0 or inp.etf_expense_ratio > 0.10:
                raise BalanceSheetInvariantError(
                    f"【工位 2 阻断】ETF {inp.ticker} 管理费率异常 ({inp.etf_expense_ratio:.4f})，超出正常区间 [0%, 10%]。"
                )
            if inp.etf_top10_weight_pct < 0.0 or inp.etf_top10_weight_pct > 100.0:
                raise BalanceSheetInvariantError(
                    f"【工位 2 阻断】ETF {inp.ticker} 前十大持仓集中度权重 ({inp.etf_top10_weight_pct:.1f}%) 超出 [0, 100%] 区间。"
                )
            return {
                "status": "PASSED",
                "is_balanced": True,
                "asset_type": "ETF",
                "nav": nav,
                "fcf": 0.0,
                "unrestricted_cash": 0.0,
                "net_cash": 0.0,
                "shares_outstanding": max(1.0, inp.shares_outstanding),
            }
        elif asset_type in ["COMMODITY_GOLD", "GOLD"]:
            # 黄金与宏观贵金属核验
            anchor = inp.gold_traditional_anchor_price if inp.gold_traditional_anchor_price > 0.0 else inp.current_price
            if inp.gold_physical_premium_pct < -0.30 or inp.gold_physical_premium_pct > 0.50:
                raise BalanceSheetInvariantError(
                    f"【工位 2 阻断】大宗商品 {inp.ticker} 实物溢价率 ({inp.gold_physical_premium_pct * 100:.1f}%) 严重偏离正常物理套利区间。"
                )
            return {
                "status": "PASSED",
                "is_balanced": True,
                "asset_type": "COMMODITY_GOLD",
                "anchor_price": anchor,
                "fcf": 0.0,
                "unrestricted_cash": 0.0,
                "net_cash": 0.0,
                "shares_outstanding": 1.0,
            }
        else:
            # 普通股官方资产负债表刚性平账自检
            assets = inp.total_assets
            liab = inp.total_liabilities
            equity = inp.stockholders_equity

            # 若三表数据全为 0（如纯指数或未披露），设置安全缺省
            if assets > 0.0 or liab > 0.0 or equity != 0.0:
                discrepancy = abs(assets - (liab + equity))
                tolerance = max(1.0, assets * 0.005)  # 允许 0.5% 内因非标附注带来的舍入误差
                if discrepancy > tolerance:
                    raise BalanceSheetInvariantError(
                        f"【工位 2 阻断】标的 {inp.ticker} 资产负债表严重失衡: "
                        f"总资产 (${assets:,.0f}) != 负债 (${liab:,.0f}) + 股东权益 (${equity:,.0f}), "
                        f"差额达 ${discrepancy:,.0f}，超出容差 ${tolerance:,.0f}。"
                    )

            # 真实造血现金流与净流动性核验
            fcf = inp.reported_operating_cash_flow - inp.reported_capex - inp.stock_based_compensation
            unrestricted_cash = max(0.0, inp.reported_cash - inp.restricted_cash - inp.debt_covenant_min_cash)
            net_cash = unrestricted_cash - inp.total_debt

            return {
                "status": "PASSED",
                "is_balanced": True,
                "asset_type": "EQUITY",
                "fcf": fcf,
                "unrestricted_cash": unrestricted_cash,
                "net_cash": net_cash,
                "shares_outstanding": max(1.0, inp.shares_outstanding),
            }

    # -------------------------------------------------------------
    # 工位 3: 宏观压力分与动态弹性安全边际 (MacroElasticMarginEngine)
    # -------------------------------------------------------------
    def station_3_macro_elastic_margin(self, inp: CanyonStationInput, filing_out: Dict[str, Any]) -> Dict[str, Any]:
        """计算宏观流动性综合压力分 S_macro，并动态调节弹性安全边际。"""
        # 1. 宏观压力分 (0.0~1.0)
        vix_component = min(1.0, max(0.0, (inp.vix_index - 15.0) / 30.0))
        yield_component = min(1.0, max(0.0, (inp.us_10y_yield - 0.035) / 0.030))
        drain_component = min(1.0, max(0.0, inp.fed_liquidity_drain_billion / 100.0))
        macro_stress_score = round(0.40 * vix_component + 0.35 * yield_component + 0.25 * drain_component, 3)

        # 2. 优质蓝筹在宏观踩踏下的“流动性提款机效应”检测 (ATM Effect)
        # 标的高流动性、优质高盈利但遇宏观高压力时，机构常被迫抛售以补衍生品保证金
        is_large_cap = inp.shares_outstanding * inp.current_price > 50e9  # 市值 > 500亿美元
        is_high_liquidity = inp.company_beta >= 0.90
        atm_effect_warning = (macro_stress_score >= 0.55) and is_large_cap and is_high_liquidity

        # 3. 动态弹性安全边际 MOS_elastic
        asset_type = (inp.asset_type or "EQUITY").upper().strip()
        if asset_type == "ETF":
            # ETF 具备成分股高度分散化属性，基准安全边际为 10%
            base_mos = 10.0
            elastic_mos = round(base_mos * (1.0 + 0.50 * macro_stress_score), 2)
        elif asset_type in ["COMMODITY_GOLD", "GOLD"]:
            # 黄金为逆周期宏观避险硬通货，基准安全边际为 12%
            base_mos = 12.0
            elastic_mos = round(base_mos * (1.0 + 0.35 * macro_stress_score), 2)
        else:
            base_mos = 15.0  # 普通股基准安全边际 15%
            elastic_mos = round(base_mos * (1.0 + 0.75 * macro_stress_score), 2)

        return {
            "macro_stress_score": macro_stress_score,
            "elastic_mos_pct": elastic_mos,
            "atm_effect_warning": atm_effect_warning,
            "effective_wacc": max(0.075, 0.045 + inp.company_beta * 0.045 + macro_stress_score * 0.02),
        }

    # -------------------------------------------------------------
    # 工位 4: 自由现金流折现三情景估值走廊 (ThreeScenarioValuation)
    # -------------------------------------------------------------
    def station_4_three_scenario_valuation(
        self, inp: CanyonStationInput, filing_out: Dict[str, Any], macro_out: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行自由现金流折现 (DCF) 或多资产估值三情景走廊测算。"""
        asset_type = (inp.asset_type or "EQUITY").upper().strip()

        if asset_type == "ETF":
            nav = filing_out.get("nav", inp.current_price)
            # 费率损耗模型: 5年持有期费率折减
            fee_drag = min(0.15, inp.etf_expense_ratio * 5.0)
            # 中性公允价值: 底层 NAV 扣除中长期费率拖累 + 赛道成长折现 (假设净年化超额 +3%)
            neutral_fair = max(0.5, nav * (1.0 + 0.03 - fee_drag))
            # 悲观防御底价: 成分股大盘杀估值 18% 叠加赎回折价
            pessimistic_floor = max(0.2, nav * 0.82)
            # 乐观弹性靶心: 赛道盈利高增与增量被动资金流入溢价
            optimistic_target = max(neutral_fair * 1.10, nav * 1.25)
            pessimistic_event = "成分股核心重仓遭遇盈利下滑与行业反垄断，跟踪误差与贴水放大"
            optimistic_event = "核心赛道贝塔爆发叠加宏观宽松流动性，指数成分股盈利持续超预期"
        elif asset_type in ["COMMODITY_GOLD", "GOLD"]:
            anchor = filing_out.get("anchor_price", inp.current_price)
            # 传统模型: 实际利率每上升 100bps，黄金折现下压约 8%~12%
            real_yield_effect = max(-0.25, min(0.25, -(inp.gold_tips_10y_real_yield - 0.015) * 8.0))
            # 央行购金结构性溢价: 净购金量每 500 吨增持支撑 +4%
            cb_premium = min(0.30, max(0.0, (inp.gold_central_bank_net_tonnes / 1000.0) * 0.08))
            physical_premium = max(-0.05, min(0.15, inp.gold_physical_premium_pct))

            neutral_fair = max(10.0, anchor * (1.0 + real_yield_effect + cb_premium + physical_premium))
            pessimistic_floor = max(5.0, anchor * 0.85)
            optimistic_target = max(neutral_fair * 1.10, anchor * 1.30)
            pessimistic_event = "实际利率大幅攀升与强势美元压制，主权央行购金放缓且实物溢价收敛"
            optimistic_event = "地缘格局割裂与去美元化储备结构性提升，实物黄金现货挤兑与法币信用对冲"
        else:
            fcf = filing_out["fcf"]
            net_cash = filing_out["net_cash"]
            shares = filing_out["shares_outstanding"]
            wacc = macro_out["effective_wacc"]

            if fcf > 0.0:
                # 持续现金流造血企业
                # 中性公允价值: 永续增长率 2.5%
                g_neut = 0.025
                denom_neut = max(0.02, wacc - g_neut)
                ev_neut = ((fcf * (1.0 + g_neut)) / denom_neut) + net_cash
                neutral_fair = max(0.5, ev_neut / shares)

                # 悲观防御底价: 利率飙升 WACC + 1.5%，永续增长率 1.0%
                g_pess = 0.010
                denom_pess = max(0.02, (wacc + 0.015) - g_pess)
                ev_pess = ((fcf * (1.0 + g_pess)) / denom_pess) + net_cash
                pessimistic_floor = max(0.2, ev_pess / shares)

                # 乐观弹性靶心: 宏观降息 WACC - 1.0%，永续增长率 3.5%
                g_opt = 0.035
                denom_opt = max(0.02, (wacc - 0.010) - g_opt)
                ev_opt = ((fcf * (1.0 + g_opt)) / denom_opt) + net_cash
                optimistic_target = max(neutral_fair * 1.10, ev_opt / shares)
            else:
                # 研发阶段或暂未盈利企业: 结合净资产/清算现金与核心营收测算
                base_val = max(1.0, net_cash + inp.reported_revenue * 1.5)
                neutral_fair = max(0.5, base_val / shares)
                pessimistic_floor = max(0.2, (net_cash + inp.reported_revenue * 0.8) / shares)
                optimistic_target = max(neutral_fair * 1.15, (net_cash + inp.reported_revenue * 3.0) / shares)

            pessimistic_event = "美联储收紧流动性叠加终端需求不及预期，估值折现率高企杀估值"
            optimistic_event = "行业周期拐点确认，海外高毛利渗透率超预期并达成降息估值修复"

        # 刚性几何单调走廊约束: 悲观底 <= 0.90 * 公允中枢 < 公允中枢 < 1.10 * 公允中枢 <= 乐观靶心
        pessimistic_floor = round(min(neutral_fair * 0.90, pessimistic_floor), 2)
        neutral_fair = round(neutral_fair, 2)
        optimistic_target = round(max(neutral_fair * 1.10, optimistic_target), 2)

        return {
            "neutral_fair_value": neutral_fair,
            "pessimistic_floor": pessimistic_floor,
            "pessimistic_event": pessimistic_event,
            "optimistic_target": optimistic_target,
            "optimistic_event": optimistic_event,
        }

    # -------------------------------------------------------------
    # 工位 5: 黄金击球买入底线与凯利仓位控制 (GoldenStrikeZoneGate)
    # -------------------------------------------------------------
    def station_5_golden_strike_zone(
        self, inp: CanyonStationInput, val_out: Dict[str, Any], macro_out: Dict[str, Any]
    ) -> Dict[str, Any]:
        """测算黄金击球买入底线 Strike Price 并判定买方区位与仓位配置。"""
        neutral_fair = val_out["neutral_fair_value"]
        elastic_mos = macro_out["elastic_mos_pct"]
        current = inp.current_price

        # 黄金击球底线 Strike Price = P_neutral * (1 - MOS_elastic / 100)
        strike_price = round(neutral_fair * (1.0 - elastic_mos / 100.0), 2)

        # 判定区位
        if current <= strike_price:
            zone_status = "GOLDEN_STRIKE_ZONE"
            rec_action = f"现价 (${current:.2f}) 击穿黄金买入底线 (${strike_price:.2f})，具备充足弹性安全边际 ({elastic_mos:.1f}%)，建议分批坚决买入建仓。"
            # 半凯利配置比例: 基于赔率与成功概率
            b = max(0.1, (val_out["optimistic_target"] - current) / max(0.01, current))
            p = 0.65  # 击球区基准胜率
            q = 1.0 - p
            full_kelly = max(0.0, (b * p - q) / b)
            half_kelly_pct = round(min(0.25, full_kelly * 0.50) * 100.0, 1)
        elif current <= neutral_fair:
            zone_status = "NEUTRAL_HOLD"
            rec_action = f"现价 (${current:.2f}) 处于黄金击球底线 (${strike_price:.2f}) 与公允中枢 (${neutral_fair:.2f}) 之间，估值适中，建议持有观察等待更好买点。"
            half_kelly_pct = 5.0
        else:
            zone_status = "PREMIUM_OVERVALUED"
            rec_action = f"现价 (${current:.2f}) 高于中性公允中枢 (${neutral_fair:.2f})，处于溢价透支区间，严禁追高，持有者宜逐步锁定利润。"
            half_kelly_pct = 0.0

        return {
            "strike_price": strike_price,
            "zone_status": zone_status,
            "recommended_action": rec_action,
            "kelly_position_pct": half_kelly_pct,
        }

    # -------------------------------------------------------------
    # 工位 6: 买方投资直觉决策卡与不可篡改时间链条 (DecisionCardAndLedger)
    # -------------------------------------------------------------
    def station_6_decision_card_and_ledger(
        self,
        inp: CanyonStationInput,
        quote_out: Dict[str, Any],
        val_out: Dict[str, Any],
        strike_out: Dict[str, Any],
        macro_out: Dict[str, Any],
    ) -> CanyonDecisionCard:
        """生成买方直觉决策卡，并写入 PredictionLedger SHA-256 不可篡改链条。"""
        # 衍生品期权评估
        if inp.option_target_strike > 0.0:
            greeks = self.volatility_engine.calculate_option_greeks(
                spot=inp.current_price,
                strike=inp.option_target_strike,
                time_to_expiry_years=max(1e-4, inp.option_expiry_days / 365.0),
                risk_free_rate=inp.us_10y_yield,
                dividend_yield=0.0,
                volatility=inp.option_implied_vol,
                option_type="call" if inp.is_call_option else "put",
            )
            theta_daily = abs(greeks.theta_daily)
            options_verdict = (
                f"行权价 ${inp.option_target_strike:.2f} 合约每日时间价值损耗为 -${theta_daily:.3f}/股 "
                f"(Delta: {greeks.delta:+.2f})。临近到期时间价值加速归零，严禁单边重仓虚值买方策略。"
            )
        else:
            options_verdict = "现货主导策略，当前未配置特定单边期权敞口。"

        # 资产类型标签映射
        asset_type = (inp.asset_type or "EQUITY").upper().strip()
        if asset_type == "ETF":
            asset_label = "核心指数与主题 ETF (ETF)"
        elif asset_type in ["COMMODITY_GOLD", "GOLD"]:
            asset_label = "黄金与宏观贵金属 (Commodity Gold)"
        else:
            asset_label = "普通股 (Equity)"

        # 写入 PredictionLedger 链条锁定指纹
        prediction_id = f"PRED-{inp.market}-{inp.ticker}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        snapshot = HistoricalPredictionSnapshot(
            prediction_id=prediction_id,
            prediction_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            market=inp.market,
            ticker=inp.ticker,
            company_name=inp.company_name,
            baseline_price=inp.current_price,
            rating=strike_out["zone_status"],
            safe_entry_trigger=strike_out["strike_price"],
            pessimistic_floor=val_out["pessimistic_floor"],
            pessimistic_event=val_out["pessimistic_event"],
            neutral_fair_value=val_out["neutral_fair_value"],
            optimistic_target=val_out["optimistic_target"],
            optimistic_event=val_out["optimistic_event"],
            tactical_action=strike_out["recommended_action"],
            kelly_fraction=strike_out["kelly_position_pct"] / 100.0,
            options_warning=options_verdict,
            falsification_signals=[
                f"宏观流动性压力分突破 0.80",
                f"自由现金流由正转负且单季资本开支超预期 20%" if asset_type == "EQUITY" else "底层资产净值跌破防御底线",
                f"击穿悲观防御底价 ${val_out['pessimistic_floor']:.2f}",
            ],
            liquidity_profile="HIGH_LIQUIDITY" if macro_out["atm_effect_warning"] else "NORMAL",
            counterparty_type="INSTITUTIONAL_BUY_SIDE",
            second_order_thesis=f"单向 6 工位线性流水线驱动 [{asset_label}]：弹性安全边际 {macro_out['elastic_mos_pct']:.1f}%",
        )

        ledger_hash = self.ledger.record_prediction(snapshot)

        return CanyonDecisionCard(
            ticker=inp.ticker,
            company_name=inp.company_name,
            market=inp.market,
            quote_timestamp=quote_out["quote_timestamp"],
            market_session_state=quote_out["session_label"],
            current_price=inp.current_price,
            asset_type=asset_type,
            asset_class_label=asset_label,
            neutral_fair_value=val_out["neutral_fair_value"],
            strike_price=strike_out["strike_price"],
            elastic_mos_pct=macro_out["elastic_mos_pct"],
            zone_status=strike_out["zone_status"],
            recommended_action=strike_out["recommended_action"],
            kelly_position_pct=strike_out["kelly_position_pct"],
            pessimistic_floor=val_out["pessimistic_floor"],
            pessimistic_event=val_out["pessimistic_event"],
            optimistic_target=val_out["optimistic_target"],
            optimistic_event=val_out["optimistic_event"],
            macro_stress_score=macro_out["macro_stress_score"],
            liquidity_atm_warning=macro_out["atm_effect_warning"],
            options_timing_verdict=options_verdict,
            ledger_hash=ledger_hash,
        )

    # -------------------------------------------------------------
    # 单向主流动流水线 (The Canyon Linear Pipeline Stream)
    # -------------------------------------------------------------
    def run(self, inp: CanyonStationInput) -> CanyonDecisionCard:
        """从工位 1 至工位 6 单向无环流动执行全链路投研分析。"""
        # 工位 1: 行情时效核验
        quote_out = self.station_1_quote_freshness(inp)

        # 工位 2: 官方财报平账
        filing_out = self.station_2_official_filing(inp)

        # 工位 3: 宏观弹性安全边际
        macro_out = self.station_3_macro_elastic_margin(inp, filing_out)

        # 工位 4: 三情景估值走廊
        val_out = self.station_4_three_scenario_valuation(inp, filing_out, macro_out)

        # 工位 5: 黄金击球底线与买方区位
        strike_out = self.station_5_golden_strike_zone(inp, val_out, macro_out)

        # 工位 6: 买方决策卡与时间链条
        card = self.station_6_decision_card_and_ledger(
            inp, quote_out, val_out, strike_out, macro_out
        )

        return card
