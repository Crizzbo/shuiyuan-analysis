"""全盘负向压力测试与财务衰退困境企业估值检验.

专用于验证金融估值引擎在面对业绩恶化、现金失血、利息无法覆盖及巨额债务墙时的防御能力与判决公正性:
1. 股东有限责任与清算残值防御 (Merton 1974: E >= 0)
2. 运营折现负值黑洞 vs 清算残值解耦
3. 达摩达兰资本内生增长检验: 资本持续侵蚀与负向隐含 ROIC 诊断
4. 僵尸企业 (Zombie Firm: ICR < 1.0) 与债务墙识别
5. 现金失血跑道 (Cash Burn Runway Months) 测算与流动性枯竭断崖
6. 机构研判排斥陷阱: 严禁将价值陷阱误判为"低估买入"，严格输出强制剔除与回避研判
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.firm_value_added_bridge_engine import (
    FirmFinancialFact,
    FirmValueAddedBridgeEngine,
)


def get_distressed_and_zombie_universe():
    """定义美股与日股真实衰退/困境企业样本库及其微观财务底账."""
    return [
        # 1. 转型重度失血巨头 (Foundry Capex Cash Bleed)
        FirmFinancialFact(
            ticker="INTC",
            company_name="Intel Corporation",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=54200.0,
            cogs_million=32500.0,
            operating_expenses_million=12200.0,
            ebitda_million=9500.0,
            wages_and_salaries_million=13100.0,
            taxes_paid_million=500.0,
            capex_million=22000.0,
            annual_fcf_million=-12500.0,  # 年自由现金流巨亏 125 亿美元
            market_cap_billion=102.5,
            country_id="US",
            foreign_revenue_ratio=0.74,
            fx_sensitivity_elasticity=0.0,
            inventory_turnover_days_dio=125.0,  # 存货周转天数大幅拉长至 125 天
            total_debt_million=52000.0,
            cash_and_equivalents_million=24000.0,
            interest_expense_million=1800.0,
            tangible_book_value_million=65000.0,
        ),
        # 2. 概念炒作严重失血僵尸 (Structural Cash Bleed & Dilution Trap)
        FirmFinancialFact(
            ticker="PLUG",
            company_name="Plug Power Inc.",
            market="US",
            sector_id="IND_MACH",
            revenue_million=710.0,
            cogs_million=1190.0,  # 毛亏损 (Gross Loss)
            operating_expenses_million=380.0,
            ebitda_million=-860.0,  # EBITDA 为负
            wages_and_salaries_million=230.0,
            taxes_paid_million=10.0,
            capex_million=250.0,
            annual_fcf_million=-1110.0,  # 年失血超 11 亿美元
            market_cap_billion=1.75,
            country_id="US",
            foreign_revenue_ratio=0.25,
            fx_sensitivity_elasticity=0.0,
            inventory_turnover_days_dio=210.0,
            total_debt_million=980.0,
            cash_and_equivalents_million=320.0,  # 账面现金仅 3.2 亿美元，跑道岌岌可危
            interest_expense_million=75.0,
            tangible_book_value_million=520.0,
        ),
        # 3. 巨额负债商业模式衰退价值陷阱 (Debt Wall & Declining Moat Value Trap)
        FirmFinancialFact(
            ticker="WBA",
            company_name="Walgreens Boots Alliance",
            market="US",
            sector_id="HEALTH_BIO",
            revenue_million=144500.0,
            cogs_million=116000.0,
            operating_expenses_million=25300.0,
            ebitda_million=3200.0,
            wages_and_salaries_million=18500.0,
            taxes_paid_million=350.0,
            capex_million=1900.0,
            annual_fcf_million=450.0,  # 现金流极度微薄
            market_cap_billion=8.2,
            country_id="US",
            foreign_revenue_ratio=0.15,
            fx_sensitivity_elasticity=0.0,
            inventory_turnover_days_dio=45.0,
            total_debt_million=33500.0,  # 335 亿美元巨额债务
            cash_and_equivalents_million=720.0,
            interest_expense_million=2650.0,  # 利息开支高达 26.5 亿，ICR 仅 1.2x
            tangible_book_value_million=-9800.0,  # 剔除商誉后有形净资产为负
        ),
        # 4. 阿吉翁创造性毁灭淘汰标的、连续十年亏损 (Aghion Creative Destruction Victim)
        FirmFinancialFact(
            ticker="6740.T",
            company_name="Japan Display Inc. (JDI)",
            market="JP",
            sector_id="TECH_SEMI",
            revenue_million=1850.0,
            cogs_million=1800.0,
            operating_expenses_million=270.0,
            ebitda_million=-220.0,  # EBITDA 亏损
            wages_and_salaries_million=310.0,
            taxes_paid_million=15.0,
            capex_million=90.0,
            annual_fcf_million=-310.0,
            market_cap_billion=0.22,  # 市值仅 2.2 亿美元
            country_id="JP",
            foreign_revenue_ratio=0.88,
            fx_sensitivity_elasticity=0.40,
            inventory_turnover_days_dio=85.0,
            total_debt_million=1150.0,
            cash_and_equivalents_million=260.0,
            interest_expense_million=28.0,
            tangible_book_value_million=-450.0,  # 资不抵债
        ),
        # 5. 重资产扩张高息债务墙危机 (Mobile Telecom Capex & Junk Bond Wall)
        FirmFinancialFact(
            ticker="4755.T",
            company_name="Rakuten Group Inc.",
            market="JP",
            sector_id="COMM_SERV",
            revenue_million=14200.0,
            cogs_million=9100.0,
            operating_expenses_million=4000.0,
            ebitda_million=1100.0,
            wages_and_salaries_million=2150.0,
            taxes_paid_million=130.0,
            capex_million=2450.0,
            annual_fcf_million=-1350.0,  # 移动基站建设导致巨额失血
            market_cap_billion=11.8,
            country_id="JP",
            foreign_revenue_ratio=0.18,
            fx_sensitivity_elasticity=0.10,
            inventory_turnover_days_dio=35.0,
            total_debt_million=22500.0,  # 负债逾 225 亿美元
            cash_and_equivalents_million=4600.0,
            interest_expense_million=1380.0,  # 利息 13.8 亿美元 > EBITDA 11.0 亿 (ICR 0.80x)
            tangible_book_value_million=3200.0,
        ),
    ]


def main():
    engine = FirmValueAddedBridgeEngine()
    distressed_firms = get_distressed_and_zombie_universe()

    print("=" * 140)
    print("[压力测试] 买方投研系统·负向测试与衰退/财务困境企业全盘压力测试 (Negative Distress & Zombie Valuation Stress Test)")
    print("=" * 140)
    print("测试目标: 验证数学引擎在企业失血 (FCF<0)、债务墙高企 (ICR<1.0)、负资产净值及濒临破产时的防御边界与判决客观性.")
    print("核心数学防御契约:")
    print("  1. 股东有限责任下界: 股权价值下界严守清算残值或零 (E >= max(Liquidation, 0.0))，彻底杜绝负股价漏洞.")
    print("  2. 运营折现负值黑洞暴露: 单独测算 raw_operational_dcf (揭示失血缺口)，与清算底价清晰解耦.")
    print("  3. 现金失血跑道预警: 测算 Cash Runway Months，对 <6 个月流动性危机企业触发最高破产红牌.")
    print("  4. 达摩达兰资本侵蚀防御: 杜绝负 EBITDA 时的虚假正 ROIC，如实报出负 ROIC 与资本毁灭状态.")
    print("  5. 机构决策严拒伪买入: 绝对禁止对陷入财务危机的企业给出'低估买入'或'逢高止盈'，坚决输出强制回避/剔除.\n")

    header = (
        f"{'代码':<7} | {'公司全称':<18} | {'市值':<8} | {'年FCF':<9} | "
        f"{'原始运营DCF':<12} | {'清算残值底':<10} | {'公允内在价值':<12} | "
        f"{'ICR利息覆盖':<10} | {'现金跑道':<8} | {'隐含ROIC':<8} | {'僵尸企业':<6} | {'机构决策研判'}"
    )
    print(header)
    print("-" * 140)

    for firm in distressed_firms:
        val = engine.compute_firm_intrinsic_valuation(firm, sector_wacc=0.080, terminal_growth_rate=0.025)
        diag = val["financial_distress_diagnostics"]
        ts = val["two_stage_valuation"]
        roic = val["endogenous_capital_consistency"]["implied_roic_pct"]

        runway_str = f"{diag['cash_burn_runway_months']:.1f}个月" if diag["cash_burn_runway_months"] is not None else "正现金流"
        icr_str = f"{diag['interest_coverage_ratio']:.2f}x" if diag["interest_coverage_ratio"] < 900 else "无利息"
        zombie_str = "【是】" if diag["is_zombie_firm"] else "否"

        line = (
            f"{firm.ticker:<7} | "
            f"{firm.company_name[:16]:<18} | "
            f"${firm.market_cap_billion:>6.1f}B | "
            f"${val['annual_fcf_million']:>7.0f}M | "
            f"${val['raw_operational_dcf_billion']:>10.1f}B | "
            f"${val['liquidation_floor_billion']:>8.1f}B | "
            f"${val['fair_intrinsic_value_billion']:>10.1f}B | "
            f"{icr_str:>10} | "
            f"{runway_str:>8} | "
            f"{roic:>7.1f}% | "
            f"{zombie_str:^6} | "
            f"{val['institutional_verdict']}"
        )
        print(line)

    print("\n" + "=" * 140)
    print("[深度诊断] 衰退与困境企业微观资产负债表与失血深度诊断明细 (Micro Balance Sheet & Distress Deep Dive)")
    print("=" * 140)

    for firm in distressed_firms:
        val = engine.compute_firm_intrinsic_valuation(firm, sector_wacc=0.080, terminal_growth_rate=0.025)
        diag = val["financial_distress_diagnostics"]
        ecc = val["endogenous_capital_consistency"]

        print(f"▶ 标的: 【{firm.ticker}】 {firm.company_name} ({firm.market})")
        print(f"  • 当前总市值: ${firm.market_cap_billion:.2f}B | 年自由现金流 (FCF): ${firm.annual_fcf_million:.1f}M | 营收: ${firm.revenue_million:.1f}M")
        print(f"  • 债务与现金流动性: 有息负债 ${diag['total_debt_million']:.1f}M | 现金储备 ${diag['cash_and_equivalents_million']:.1f}M | 净债务: ${diag['total_debt_million'] - diag['cash_and_equivalents_million']:.1f}M")
        print(f"  • 偿债与利息覆盖: 年利息开支 ${diag['interest_expense_million']:.1f}M | 利息保障倍数 (ICR): {diag['interest_coverage_ratio']:.2f}x | 负债/EBITDA: {diag['debt_to_ebitda_ratio']:.2f}x")
        print(f"  • 存活跑道与清算残值: 现金失血跑道: {diag['cash_burn_runway_months']} 个月 | 有形净资产: ${diag['tangible_book_value_million']:.1f}M | 破产清算底价: ${val['liquidation_floor_billion']:.2f}B")
        print(f"  • 达摩达兰资本内生增长: 隐含 ROIC: {ecc['implied_roic_pct']:.2f}% | 状态: {ecc['capital_status']}")
        print(f"  • 运营折现 vs 股权下界: 原始运营折现黑洞: ${val['raw_operational_dcf_billion']:.2f}B | 两阶段折现黑洞: ${val['two_stage_valuation']['raw_two_stage_operational_dcf_billion']:.2f}B")
        print(f"  • 最终股东公允价值: ${val['fair_intrinsic_value_billion']:.2f}B (两阶段: ${val['two_stage_valuation']['two_stage_fair_value_billion']:.2f}B)")
        print(f"  • 机构研判结论: 【{val['institutional_verdict']}】")
        print(f"  • 投资实操建议: 【{val['recommended_action']}】\n")


if __name__ == "__main__":
    main()
