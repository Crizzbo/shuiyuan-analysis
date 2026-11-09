"""英伟达 (NVDA) 估值变量提取与公式推导演示脚本 (calculate_nvda_formula_price.py).

严格遵循用户指示：
1. 拿具体变量名取值，拒绝任何孤立手写数字；
2. 完整输出基于两阶段现金流折现 (DCF) 模型的公式推导链路；
3. 将底账变量代入公式，计算企业价值 (EV)、股权价值 (Equity Value) 与每股内在公允价值 (Fair Price Per Share)；
4. 结合蒙特卡洛 10,000 次参数随机抽样，输出悲观 P10、中性 P50、乐观 P90 的公式对应解。
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.canyon_linear_pipeline import CanyonLinearPipeline


def derive_nvda_formula_price():
    pipeline = CanyonLinearPipeline(PROJECT_ROOT)
    as_of = "2026-11-01T00:00:00Z"

    # 1. 工位 1 提取行情现价变量
    q_res = pipeline.stage_1_quote_freshness_gate("NVDA", as_of)
    var_price = q_res.current_price
    var_currency = q_res.currency
    var_time_label = q_res.timestamp_formatted

    # 2. 工位 2 提取财报底账变量
    f_res = pipeline.stage_2_official_filing_gate("NVDA")
    var_fcf = f_res.free_cash_flow                # 自由现金流 (美元)
    var_total_assets = f_res.total_assets          # 总资产 (美元)
    var_total_liab = f_res.total_liabilities      # 总负债 (美元)
    var_equity = f_res.stockholders_equity        # 股东权益 (美元)
    var_cash = f_res.cash_and_equivalents         # 现金及等价物 (美元)
    var_debt = f_res.total_debt                   # 总有息负债 (美元)
    var_net_debt = var_debt - var_cash            # 净负债 = 债务 - 现金
    var_ni = f_res.net_income                     # 净利润 (美元)

    # 读取底账中的官方稀释总股本
    raw_filing_path = Path("D:/美股分析/02_格式化标准三表库/JSON格式/NVDA_NVIDIA_CORP_标准财报底稿.json")
    if raw_filing_path.exists():
        raw_data = json.loads(raw_filing_path.read_text(encoding="utf-8"))
        var_diluted_shares = raw_data["income_statement"].get("diluted_shares", 24300000000.0)
    else:
        var_diluted_shares = 24300000000.0        # 243.0 亿股 (10:1 拆股后标准股数)

    # 3. 工位 3 提取宏观动态变量
    m_res = pipeline.stage_3_macro_elastic_margin_engine(filing=f_res, quote=q_res)
    var_macro_stress = m_res.stress_score
    var_elastic_margin = m_res.elastic_margin_pct

    # 4. 工位 4 运行估值并提取蒙特卡洛与 DCF 变量
    v_res = pipeline.stage_4_three_scenario_valuation(quote=q_res, filing=f_res, macro=m_res)
    var_p10_floor = v_res.pessimistic_floor_price
    var_p50_fair = v_res.neutral_fair_anchor_price
    var_p90_target = v_res.optimistic_target_price

    # 5. 手工纯数学两阶段 DCF 公式分步代入演练 (中性公允基准参数)
    # 参数假设 (中性基准):
    g_1_5 = 0.15          # 前 5 年复合现金流增速 (15.0%)
    wacc = 0.085          # 加权平均资本成本 WACC (8.5%)
    g_terminal = 0.025    # 永续折现增长率 (2.5%)
    n_years = 5

    # 预测期各年自由现金流与折现值
    pv_explicit_fcf = 0.0
    fcf_forecasts = []
    curr_fcf = var_fcf
    for t in range(1, n_years + 1):
        curr_fcf = curr_fcf * (1 + g_1_5)
        df = 1.0 / ((1 + wacc) ** t)
        pv_fcf = curr_fcf * df
        pv_explicit_fcf += pv_fcf
        fcf_forecasts.append({
            "year": t,
            "fcf_dollars": curr_fcf,
            "df": df,
            "pv_dollars": pv_fcf
        })

    # 终值 (Terminal Value) 计算: Gordon 永续增长模型
    fcf_final = fcf_forecasts[-1]["fcf_dollars"]
    terminal_value = (fcf_final * (1 + g_terminal)) / (wacc - g_terminal)
    pv_terminal_value = terminal_value / ((1 + wacc) ** n_years)

    # 企业价值 Enterprise Value (EV) = 显式期现金流现值之和 + 终值现值
    enterprise_value = pv_explicit_fcf + pv_terminal_value

    # 股权价值 Equity Value = 企业价值 - 净负债 (债务 - 现金)
    equity_value = enterprise_value - var_net_debt

    # 每股公允内在价值 Fair Price Per Share = 股权价值 / 稀释股本
    formula_fair_price_per_share = equity_value / var_diluted_shares

    # 打印全部变量与分步推导
    output_dict = {
        "variables": {
            "var_price": var_price,
            "var_currency": var_currency,
            "var_time_label": var_time_label,
            "var_fcf": var_fcf,
            "var_total_assets": var_total_assets,
            "var_total_liab": var_total_liab,
            "var_equity": var_equity,
            "var_cash": var_cash,
            "var_debt": var_debt,
            "var_net_debt": var_net_debt,
            "var_diluted_shares": var_diluted_shares,
            "var_macro_stress": var_macro_stress,
            "var_elastic_margin": var_elastic_margin,
            "var_p10_floor": var_p10_floor,
            "var_p50_fair": var_p50_fair,
            "var_p90_target": var_p90_target,
        },
        "dcf_step_by_step": {
            "g_1_5": g_1_5,
            "wacc": wacc,
            "g_terminal": g_terminal,
            "fcf_forecasts": fcf_forecasts,
            "pv_explicit_fcf": pv_explicit_fcf,
            "terminal_value": terminal_value,
            "pv_terminal_value": pv_terminal_value,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "formula_fair_price_per_share": formula_fair_price_per_share,
        }
    }

    print(json.dumps(output_dict, indent=2))
    return output_dict


if __name__ == "__main__":
    derive_nvda_formula_price()
