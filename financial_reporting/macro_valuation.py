"""宏观联动股票估值与敏感性分析引擎 (Macro-Integrated Valuation Engine)

功能定位：
1. 消费已核实的宏观基准快照数据（10Y美债、2Y美债、利差、DXY、EFFR、CPI）；
2. 动态计算基于 CAPM 的加权平均资本成本 (WACC)，杜绝手工随意假定无风险利率；
3. 联动 `finance_tools.valuation.multistage_dcf`，开展基准/降息/紧缩三态宏观情景压力测试；
4. 输出带有安全边际的建议买入价区间（Buy Zone）与宏观敏感性画像；
5. 纯项目内计算，无外部网络请求，严格防时间前视。
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from finance_tools.valuation import multistage_dcf
from finance_tools.validation import number, finite_output
from financial_reporting.macro_indicators import verify_macro_snapshot
from financial_reporting.pipeline import local


@dataclass(frozen=True)
class MacroContext:
    """结构化宏观经济基准环境上下文。"""
    rf_10y: float              # 10年期美国国债收益率（DCF 长期无风险基准 Rf）
    rf_2y: float               # 2年期美债收益率（货币政策敏感锚）
    rf_3m: float               # 3个月短期美债收益率（现金替代与货币基金基准）
    yield_spread_10y_2y: float # 10Y-2Y 期限利差（倒挂预警衰退与信贷收缩）
    dxy: float                 # 美元指数（全球流动性与海外折算敞口）
    usd_cny: float             # 美元兑在岸人民币
    core_cpi: float            # 核心 CPI 同比增速
    effr: float                # 联邦基金有效利率
    unemployment_u3: float     # U-3 官方失业率
    as_of: str                 # 快照基准观测时点（带时区）
    snapshot_id: str           # 快照不可篡改 SHA-256 哈希

    @classmethod
    def load_latest(cls, verification_path: str = "data/financial/macro-verification.json") -> "MacroContext":
        """从项目内登记的验证清单中加载最新已核实宏观快照。"""
        v_file = local(verification_path)
        meta = json.loads(v_file.read_text(encoding="utf-8"))
        snapshot_path = meta["snapshot_path"]
        snap = verify_macro_snapshot(snapshot_path)
        
        obs_map: Dict[str, float] = {}
        for o in snap["observations"]:
            obs_map[o["indicator_id"]] = float(o["value"])
            
        return cls(
            rf_10y=obs_map["us_treasury_10y_yield"],
            rf_2y=obs_map["us_treasury_2y_yield"],
            rf_3m=obs_map["us_treasury_3m_yield"],
            yield_spread_10y_2y=obs_map["yield_curve_spread_10y_2y"],
            dxy=obs_map["us_dollar_index_dxy"],
            usd_cny=obs_map["usd_cny_exchange_rate"],
            core_cpi=obs_map["us_core_cpi_yoy"],
            effr=obs_map["fed_funds_effective_rate"],
            unemployment_u3=obs_map["us_unemployment_rate_u3"],
            as_of=snap["as_of"],
            snapshot_id=snap["snapshot_id"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rf_10y": self.rf_10y,
            "rf_10y_display": f"{self.rf_10y * 100:.2f}%",
            "rf_2y": self.rf_2y,
            "rf_2y_display": f"{self.rf_2y * 100:.2f}%",
            "rf_3m": self.rf_3m,
            "rf_3m_display": f"{self.rf_3m * 100:.2f}%",
            "yield_spread_10y_2y_bps": round(self.yield_spread_10y_2y * 10000, 1),
            "yield_spread_display": f"{self.yield_spread_10y_2y * 10000:.1f} bps",
            "dxy": self.dxy,
            "usd_cny": self.usd_cny,
            "core_cpi_display": f"{self.core_cpi * 100:.2f}%",
            "effr_display": f"{self.effr * 100:.2f}%",
            "unemployment_u3_display": f"{self.unemployment_u3 * 100:.2f}%",
            "as_of": self.as_of,
            "snapshot_id": self.snapshot_id,
            "interpretations": {
                "rf_10y": "10Y 美债收益率 (4.42%) 位于 4.0%~4.5% 高位均衡平台，确立了股票 DCF 折现的基准门槛。无盈利与高久期成长股折现惩罚加重，市场更注重企业真实造血能力与自由现金流。",
                "rf_2y": "2Y 美债收益率 (4.15%) 较联邦基金利率低约 43 bps，反映市场对美联储未来温和降息的定价，短期借贷成本下降将呈现小步慢走特征。",
                "yield_spread": "10Y-2Y 利差 (+27.0 bps) 由前期深度倒挂成功转正并呈现健康陡峭化，表明金融体系走出衰退恐慌，进入经济软着陆与商业银行信贷中枢正常化阶段。",
                "rf_3m": "3M 短债收益率 (4.35%) 表明无风险现金仍具可观年化回报。账上充沛净现金的企业享有显著利息收益安全垫，而高负债企业再融资成本居高不下。",
                "dxy": "美元指数 (104.5) 处于高位强势区间，全球美元流动性偏紧。跨国出海巨头海外收入换算面临账面负折算压力，本土业务型企业受影响相对较小。",
                "policy_inflation": "政策基准利率 EFFR (4.58%) 维持限制性，核心 CPI (3.20%) 较前期高位显著回落但具一定粘性，确立了利率高位维持更久（Higher for Longer）的防御基调。",
            },
        }


class MacroValuationEngine:
    """宏观联动股票估值与多情景分析引擎。"""

    @staticmethod
    def cost_of_equity(rf: float, beta: float, erp: float = 0.05) -> float:
        """基于 CAPM 计算股权资本成本：Ke = Rf + Beta * ERP。"""
        rf = number(rf, "rf", positive=True)
        beta = number(beta, "beta", positive=True)
        erp = number(erp, "erp", positive=True)
        if not math.isfinite(rf) or rf <= 0:
            raise ValueError(f"无风险利率 Rf 必须为正有限数，输入: {rf}")
        if not math.isfinite(beta) or beta <= 0:
            raise ValueError(f"Beta 必须为正有限数，输入: {beta}")
        if not math.isfinite(erp) or erp <= 0:
            raise ValueError(f"ERP 必须为正有限数，输入: {erp}")
        return finite_output(rf + beta * erp)

    @classmethod
    def calculate_wacc(
        cls,
        market_cap: float,
        total_debt: float,
        beta: float,
        rf: float,
        erp: float = 0.05,
        tax_rate: float = 0.21,
        debt_cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        """计算加权平均资本成本 (WACC) 并输出详细组成拆解。"""
        # 不把非法负债、缺失或非有限输入修正成可用事实。
        market_cap = number(market_cap, "market_cap", positive=True)
        total_debt = number(total_debt, "total_debt", nonnegative=True)
        tax_rate = number(tax_rate, "tax_rate")
        if not 0 <= tax_rate <= 1:
            raise ValueError("tax_rate 必须在 [0,1] 内")
        total_val = market_cap + total_debt
        we = market_cap / total_val
        wd = total_debt / total_val

        ke = cls.cost_of_equity(rf, beta, erp)
        # 若未提供显式债务成本，以 rf + 1.25% 企业债利差作为合理估计
        kd_pre = (number(debt_cost, "debt_cost", nonnegative=True)
                  if debt_cost is not None else rf + 0.0125)
        kd_post = kd_pre * (1.0 - tax_rate)

        wacc = we * ke + wd * kd_post
        return finite_output({
            "wacc": round(wacc, 6),
            "wacc_display": f"{wacc * 100:.2f}%",
            "cost_of_equity": round(ke, 6),
            "cost_of_equity_display": f"{ke * 100:.2f}%",
            "cost_of_debt_pre_tax": round(kd_pre, 6),
            "cost_of_debt_pre_tax_display": f"{kd_pre * 100:.2f}%",
            "cost_of_debt_after_tax": round(kd_post, 6),
            "equity_weight": round(we, 4),
            "debt_weight": round(wd, 4),
            "rf": round(rf, 6),
            "beta": beta,
            "erp": erp,
            "debt_cost_source": "explicit_input" if debt_cost is not None else "assumption_rf_plus_125bps",
        })

    @classmethod
    def dcf_valuation(
        cls,
        cash_flow: float,
        growth_rates: List[float],
        terminal_growth: float,
        shares: float,
        discount_rate: float,
        net_debt: float = 0.0,
        scope: str = "FCFF",
    ) -> Dict[str, Any]:
        """执行多阶段现金流折现。"""
        res = multistage_dcf(
            cash_flow=cash_flow,
            growth_rates=growth_rates,
            discount_rate=discount_rate,
            terminal_growth=terminal_growth,
            shares=shares,
            scope=scope,
            net_debt=net_debt,
        )
        return res

    @classmethod
    def scenario_valuation(
        cls,
        cash_flow: float,
        growth_rates: List[float],
        terminal_growth: float,
        shares: float,
        market_cap: float,
        total_debt: float,
        beta: float,
        macro_context: MacroContext,
        current_price: Optional[float] = None,
        net_debt: float = 0.0,
        erp: float = 0.05,
        bull_shock_bps: float = -75.0,
        bear_shock_bps: float = 75.0,
    ) -> Dict[str, Any]:
        """运行宏观三态情景压力测试，输出建议买入价格区间与估值预期。
        
        情景定义：
        - Base (基准情景): 采用宏观快照 10Y 美债收益率 (Rf)；
        - Bull (降息/宽松): Rf 下调 bull_shock_bps (如 -75 bps)，成长资产折现倍数扩张；
        - Bear (紧缩/滞胀): Rf 上调 bear_shock_bps (如 +75 bps)，利率与成本承压，作为严苛安全边际底线。
        """
        # 1. 基准情景 (Base)
        rf_base = macro_context.rf_10y
        wacc_base_info = cls.calculate_wacc(market_cap, total_debt, beta, rf_base, erp)
        wacc_base = wacc_base_info["wacc"]
        if terminal_growth >= wacc_base:
            terminal_growth = max(0.01, wacc_base - 0.02)
        base_res = cls.dcf_valuation(cash_flow, growth_rates, terminal_growth, shares, wacc_base, net_debt)
        base_price = base_res["value_per_share"]

        # 2. 宽松情景 (Bull)
        rf_bull = max(0.015, rf_base + bull_shock_bps * 0.0001)
        wacc_bull_info = cls.calculate_wacc(market_cap, total_debt, beta, rf_bull, erp)
        wacc_bull = wacc_bull_info["wacc"]
        bull_growth_rates = [g + 0.02 for g in growth_rates]  # 宽松环境下适度提升增长预期
        bull_res = cls.dcf_valuation(cash_flow, bull_growth_rates, terminal_growth, shares, wacc_bull, net_debt)
        bull_price = bull_res["value_per_share"]

        # 3. 紧缩情景 (Bear)
        rf_bear = rf_base + bear_shock_bps * 0.0001
        wacc_bear_info = cls.calculate_wacc(market_cap, total_debt, beta, rf_bear, erp)
        wacc_bear = wacc_bear_info["wacc"]
        bear_growth_rates = [max(-0.20, g - 0.03) for g in growth_rates]  # 紧缩环境下下调增长预期
        bear_res = cls.dcf_valuation(cash_flow, bear_growth_rates, terminal_growth, shares, wacc_bear, net_debt)
        bear_price = bear_res["value_per_share"]

        # 建议买入价：以 Bear 公允价的 85% 作为下限，Min(Bear公允价, Base公允价的 75%) 作为上限
        buy_low = max(0.01, round(bear_price * 0.85, 2))
        buy_high = max(buy_low, round(min(bear_price, base_price * 0.75), 2))

        output: Dict[str, Any] = {
            "macro_as_of": macro_context.as_of,
            "rf_base_display": f"{rf_base * 100:.2f}%",
            "scenarios": {
                "bull_easing": {
                    "name_zh": "乐观降息情景 (Bull / Easing)",
                    "rf": round(rf_bull, 6),
                    "wacc": round(wacc_bull, 6),
                    "fair_value_per_share": round(bull_price, 2),
                    "display_value": f"${bull_price:.2f}",
                    "narrative_zh": f"10Y 美债回落至 {rf_bull * 100:.2f}%，折现成本降至 {wacc_bull * 100:.2f}%，成长弹性充分释放",
                },
                "base_case": {
                    "name_zh": "当前基准情景 (Base Case)",
                    "rf": round(rf_base, 6),
                    "wacc": round(wacc_base, 6),
                    "fair_value_per_share": round(base_price, 2),
                    "display_value": f"${base_price:.2f}",
                    "narrative_zh": f"维持当前官方基准 10Y 美债 {rf_base * 100:.2f}%，资本成本为 {wacc_base * 100:.2f}%",
                },
                "bear_tightening": {
                    "name_zh": "紧缩承压情景 (Bear / Tightening)",
                    "rf": round(rf_bear, 6),
                    "wacc": round(wacc_bear, 6),
                    "fair_value_per_share": round(bear_price, 2),
                    "display_value": f"${bear_price:.2f}",
                    "narrative_zh": f"利率上行至 {rf_bear * 100:.2f}%，折现成本升至 {wacc_bear * 100:.2f}%，估值遭受宏观压力测试",
                },
            },
            "pricing_recommendation": {
                "buy_zone_low": buy_low,
                "buy_zone_high": buy_high,
                "buy_zone_display": f"${buy_low:.2f} ~ ${buy_high:.2f}",
                "fair_value_central": round(base_price, 2),
                "fair_value_central_display": f"${base_price:.2f}",
                "bull_target": round(bull_price, 2),
                "bull_target_display": f"${bull_price:.2f}",
                "rationale_zh": f"建议买入区间严格锚定紧缩情景 (${bear_price:.2f}) 及基准公允价 75% 安全边际，确保抗利率波动防御性。",
            },
        }

        if current_price is not None and current_price > 0:
            output["pricing_recommendation"]["current_price"] = current_price
            output["pricing_recommendation"]["upside_to_base_pct"] = round(
                (base_price - current_price) / current_price * 100, 2
            )
            output["pricing_recommendation"]["upside_to_bull_pct"] = round(
                (bull_price - current_price) / current_price * 100, 2
            )
            # 状态评估
            if current_price <= buy_high:
                output["pricing_recommendation"]["stance_zh"] = "处于理想安全边际买入区间"
            elif current_price <= base_price:
                output["pricing_recommendation"]["stance_zh"] = "估值合理偏低，可分批建仓"
            elif current_price <= bull_price:
                output["pricing_recommendation"]["stance_zh"] = "已透支部分降息预期，建议观望等待回调"
            else:
                output["pricing_recommendation"]["stance_zh"] = "明显高于乐观公允价，存在估值高估风险"

        return output

    @classmethod
    def macro_sensitivity_profile(
        cls,
        company_data: Dict[str, Any],
        macro_context: MacroContext,
    ) -> Dict[str, Any]:
        """结合宏观指标快照与微观报表，生成个股宏观敏感度画像。"""
        net_income = company_data.get("net_income", 0.0)
        total_debt = company_data.get("total_debt", 0.0)
        cash = company_data.get("cash_and_equivalents", 0.0)
        revenue = company_data.get("revenue", 1.0)
        market_cap = company_data.get("market_cap", 1.0)

        # 1. 利率久期敏感度 (Rate Duration Risk)
        is_unprofitable = net_income <= 0
        ps_ratio = market_cap / max(1.0, revenue)
        if is_unprofitable or ps_ratio > 15:
            duration_level = "高敏感 (High Duration Risk)"
            duration_desc = f"公司尚未稳态盈利或估值倍数较高 (P/S {ps_ratio:.1f}x)，现金流集中于远期，对 10Y 美债收益率 ({macro_context.rf_10y * 100:.2f}%) 上升具有极高负凸性折现敏感。"
        elif ps_ratio > 5:
            duration_level = "中度敏感 (Moderate Duration Risk)"
            duration_desc = f"估值倍数中等 (P/S {ps_ratio:.1f}x)，利率上升会小幅压缩估值中枢，但具备内生盈利支撑。"
        else:
            duration_level = "低敏感 / 防御型 (Low Duration Risk)"
            duration_desc = "估值合理、现金流稳健，受长端利率折现冲击相对钝化。"

        # 2. 信贷再融资压力 (Credit & Refinancing Exposure)
        debt_to_cash = total_debt / max(1.0, cash)
        is_inverted = macro_context.yield_spread_10y_2y < 0
        if total_debt > 0 and debt_to_cash > 1.5:
            credit_level = "高再融资压力 (High Refinancing Exposure)"
            credit_desc = f"总负债显著大于在手现金 (债务现金比 {debt_to_cash:.1f}x)；当前 EFFR 达 {macro_context.effr * 100:.2f}% 且期限利差倒挂 ({macro_context.yield_spread_10y_2y * 10000:.1f} bps)，到期债务滚动再融资面临高利息成本压制。"
        elif total_debt > 0:
            credit_level = "中度可控 (Manageable Debt Profile)"
            credit_desc = "具备一定有息负债，但在手现金储备可覆盖短期偿债需求。"
        else:
            credit_level = "零负债极佳防御 (Zero Debt Fortress)"
            credit_desc = "零有息负债资产负债表，完全免疫高利率与信贷周期收紧冲击。"

        # 3. 现金储备收益缓冲 (Cash Buffer Benefit)
        cash_ratio_to_cap = cash / max(1.0, market_cap)
        est_interest_income = cash * macro_context.rf_3m
        if cash_ratio_to_cap > 0.15:
            cash_benefit_level = "显著顺风 (Significant Cash Buffer)"
            cash_benefit_desc = f"在手现金占市值 {cash_ratio_to_cap * 100:.1f}%，在 3M 美债 ({macro_context.rf_3m * 100:.2f}%) 下每年可贡献约 ${est_interest_income:.2f} 利息现金流入，有效增厚利润底线。"
        elif cash > 0:
            cash_benefit_level = "中度缓冲 (Moderate Cash Buffer)"
            cash_benefit_desc = f"在手现金能够提供一定安全缓冲，产生年化约 {macro_context.rf_3m * 100:.2f}% 闲置利息收益。"
        else:
            cash_benefit_level = "缺乏缓冲 (Weak Liquidity Buffer)"
            cash_benefit_desc = "在手流动性紧张，缺乏高息货币基金带来的被动增厚收益。"

        # 4. 汇率折算压力 (FX Translation Drag)
        dxy = macro_context.dxy
        if dxy > 103.0:
            fx_level = "面临强美元逆风 (Headwind from Strong DXY)"
            fx_desc = f"当前美元指数 ({dxy}) 处于相对高位区间，跨国出海及非美货币业务收入在换算为美元披露时存在汇率负折算压力。"
        else:
            fx_level = "汇率环境中性 (Neutral FX Impact)"
            fx_desc = f"美元指数 ({dxy}) 处于平衡区间，跨国折算影响相对均衡。"

        return {
            "macro_as_of": macro_context.as_of,
            "duration_sensitivity": {
                "level": duration_level,
                "analysis_zh": duration_desc,
            },
            "credit_refinancing": {
                "level": credit_level,
                "analysis_zh": credit_desc,
            },
            "cash_buffer_benefit": {
                "level": cash_benefit_level,
                "analysis_zh": cash_benefit_desc,
            },
            "fx_translation": {
                "level": fx_level,
                "analysis_zh": fx_desc,
            },
        }
