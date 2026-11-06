"""中观投入产出价格冲击向微观企业毛利率传导桥梁 (Industry Price Shock Bridge).

物理架构定界 (Layer 1: financial_core):
- 纯净底层架构，纯相对导入，零外层依赖;
- 结合全球列昂惕夫投入产出双对偶价格体系 (Leontief Dual Price System) 与霍尔微观加价率理论，
  定量测算宏观上游大宗/芯片/能源价格外生冲击沿产业链对中下游各行业的综合成本推升幅度，
  并结合微观企业的转嫁能力推导企业有效毛利率与经营性现金流变化;
- 遵循自然语言汇报规范：以通俗易懂的商业大白话输出买方投资结论，杜绝数学公式堆砌与 Emoji 表情。
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import math

from .global_input_output_engine import GlobalInputOutputEngine
from .industry_taxonomy_bridge import IndustryTaxonomyBridge, IndustryMappingRecord


@dataclass
class IndustryPriceShockResult:
    """产业链价格冲击与微观毛利率传导结果."""
    industry_id: str                      # 细分行业 ID
    industry_name_zh: str                 # 行业中文名
    macro_sector_id: str                  # 对应 OECD 宏观投入产出部门
    supply_chain_cost_inflation_pct: float# 产业链物料成本推升幅度 % (来自列昂惕夫双对偶)
    cost_pass_through_ratio_pct: float    # 企业成本向终端客户的转嫁能力 % (基于霍尔加价率)
    gross_margin_impact_pct: float        # 毛利率受挤压变动点位 % (例如 -1.8% 代表毛利率下降 1.8 个百分点)
    shocked_operating_margin_pct: float   # 冲击后有效营业利润率 %
    commercial_diagnosis: str             # 通俗商业大白话分析结论 (买方投资视角)


class IndustryPriceShockBridge:
    """产业链投入产出与微观毛利传导桥梁中枢."""

    def __init__(self, io_engine: Optional[GlobalInputOutputEngine] = None):
        self.version = "1.0.0"
        self.taxonomy_bridge = IndustryTaxonomyBridge()
        self.io_engine = io_engine or GlobalInputOutputEngine()

    def evaluate_supply_chain_shock(
        self,
        industry_id: str,
        macro_cost_shocks: Dict[str, float],
        company_markup: Optional[float] = None,
        cogs_ratio: Optional[float] = None,
        baseline_operating_margin: float = 0.20,
    ) -> IndustryPriceShockResult:
        """测算上游外生冲击对指定行业微观企业毛利率与盈利能力的传导冲击.

        参数:
            industry_id: 细分行业代码 (例如 "semiconductors", "autos", "food_beverage")
            macro_cost_shocks: 宏观上游部门单位增加值成本外生冲击比例字典
                               (例如 {"ENERGY_MIN": 0.20, "TECH_SEMI": -0.10})
            company_markup: 企业微观霍尔加价率 (若为 None 则采用行业先验)
            cogs_ratio: 营业成本率 COGS / Revenue (若为 None 则采用行业先验)
            baseline_operating_margin: 冲击前基准营业利润率 (默认 0.20 即 20%)
        """
        # 1. 解析细分行业映射档案
        rec = self.taxonomy_bridge.get_record(industry_id)
        effective_markup = company_markup if company_markup is not None else rec.typical_markup_ratio
        effective_cogs = cogs_ratio if cogs_ratio is not None else rec.typical_cogs_ratio

        # 2. 调用列昂惕夫双对偶价格模型计算全社会 12 大宏观部门的价格冲击
        dual_res = self.io_engine.solve_leontief_dual_price_system(macro_cost_shocks)
        sector_responses = dual_res.get("sector_price_responses", [])

        # 3. 提取企业所在宏观部门的供应链综合成本推升幅度
        chain_inflation_pct = 0.0
        for resp in sector_responses:
            if resp.get("sector_id") == rec.macro_sector_id:
                chain_inflation_pct = resp.get("supply_chain_price_impact_pct", 0.0)
                break

        # 4. 基于微观霍尔加价率计算企业转嫁能力 (Pass-through Elasticity)
        # 加价率低于 0.95: 议价权极弱，转嫁能力为 0%
        # 加价率高于 1.20: 具备超强护城河，转嫁能力达到 100%
        if effective_markup <= 0.95:
            pass_through = 0.0
        elif effective_markup >= 1.20:
            pass_through = 1.0
        else:
            pass_through = (effective_markup - 0.95) / (1.20 - 0.95)

        # 5. 传导至企业毛利率与营业利润率
        # 未被转嫁的通胀部分直接侵蚀营业成本
        unabsorbed_cost_inflation = (chain_inflation_pct / 100.0) * (1.0 - pass_through)
        gross_margin_drag = - (unabsorbed_cost_inflation * effective_cogs) * 100.0

        shocked_margin = max(-50.0, (baseline_operating_margin * 100.0) + gross_margin_drag)

        # 6. 生成通俗商业投资大白话诊断结论
        pass_through_pct = pass_through * 100.0
        if chain_inflation_pct > 0.0:
            if pass_through >= 0.80:
                diagnosis = (
                    f"上游供应链物料成本上涨 {chain_inflation_pct:.1f}%，但因企业拥有极高微观定价壁垒"
                    f"（加价率达 {effective_markup:.2f}），能够将 {pass_through_pct:.0f}% 的成本涨幅平稳顺价至下游终端，"
                    f"毛利率仅微受扰动 {gross_margin_drag:.1f} 个百分点，盈利中枢高度稳健。"
                )
            elif pass_through <= 0.25:
                diagnosis = (
                    f"上游供应链物料成本上涨 {chain_inflation_pct:.1f}%，企业议价地位处于弱势"
                    f"（加价率仅为 {effective_markup:.2f}），转嫁能力仅 {pass_through_pct:.0f}%，"
                    f"成本涨幅大部分被自身毛利吸收，导致营业利润率承压下滑至 {shocked_margin:.1f}%。"
                )
            else:
                diagnosis = (
                    f"上游供应链成本推升 {chain_inflation_pct:.1f}%，企业具备中等成本消化能力（转嫁率 {pass_through_pct:.0f}%），"
                    f"营业利润率调整为 {shocked_margin:.1f}%，需关注下游客户对涨价的接受程度。"
                )
        elif chain_inflation_pct < 0.0:
            if pass_through <= 0.50:
                diagnosis = (
                    f"上游核心要素成本下降 {abs(chain_inflation_pct):.1f}%，企业无须大幅降价即可截留成本红利，"
                    f"毛利率出现扩张修复（提振 +{abs(gross_margin_drag):.1f} 个百分点），经营造血能力明显增强。"
                )
            else:
                diagnosis = (
                    f"上游要素成本下降 {abs(chain_inflation_pct):.1f}%，行业竞争充分，成本红利将快速传导至终端售价，"
                    f"对企业净利率的提振较为温和。"
                )
        else:
            diagnosis = "当前宏观外生冲击未对该产业链核心成本造成显著异动，毛利率维持基准中枢。"

        return IndustryPriceShockResult(
            industry_id=rec.industry_id,
            industry_name_zh=rec.industry_name_zh,
            macro_sector_id=rec.macro_sector_id,
            supply_chain_cost_inflation_pct=round(chain_inflation_pct, 2),
            cost_pass_through_ratio_pct=round(pass_through_pct, 1),
            gross_margin_impact_pct=round(gross_margin_drag, 2),
            shocked_operating_margin_pct=round(shocked_margin, 2),
            commercial_diagnosis=diagnosis,
        )
