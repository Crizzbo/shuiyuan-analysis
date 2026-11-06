"""跨国贸易与开放经济宏观进出口引擎 (Inter-Country Trade & Open Economy Engine).

理论基础与数学架构:
1. 开放经济国民收入恒等式 (Open Economy National Income Identity):
   Y_i = C_i + I_i + G_i + (X_i - M_i)
   其中 X_i 为国家/地区的商品与服务出口总额，M_i 为进口总额，NX_i = X_i - M_i 为净出口。
2. 全球贸易守恒律 (Global Trade Conservation Invariant):
   在行星尺度（地球整体经济），所有国家出口总和必等于所有国家进口总和：
   sum_{i} X_i === sum_{i} M_i  ==>  sum_{i} NX_i === 0.0
3. 双边贸易流动与列昂惕夫传导矩阵 (Bilateral Trade Flow Matrix T_{ij}):
   T_{ij} 为国家 i 向国家 j 的直接出口。
   X_i = sum_{j != i} T_{ij} (国家 i 的总出口)
   M_j = sum_{i != j} T_{ij} (国家 j 的总进口)
4. 汇率与关税弹性传导 (Exchange Rate & Tariff Pass-Through):
   - 汇率变动对出口本币计价收入与外币竞争力的马歇尔-勒纳弹性 (Marshall-Lerner Condition);
   - 关税摩擦对贸易量的边际收缩效应。
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class RegionTradeProfile:
    """国家/地区开放经济贸易概况档案."""
    region_id: str
    region_name_zh: str
    region_name_en: str
    nominal_gdp_trillion: float
    gross_exports_trillion: float
    gross_imports_trillion: float
    net_exports_trillion: float
    export_openness_pct: float
    import_penetration_pct: float
    currency: str
    trade_regime: str


class InterCountryTradeEngine:
    """跨国贸易与开放经济全息平衡引擎."""

    DEFAULT_BENCHMARK_PATH = ROOT / "data" / "macro" / "inter_country_trade_benchmark.json"

    def __init__(self, benchmark_file: Optional[Path] = None):
        self.benchmark_path = benchmark_file or self.DEFAULT_BENCHMARK_PATH
        self.regions: List[RegionTradeProfile] = []
        self.region_ids: List[str] = []
        self.region_map: Dict[str, RegionTradeProfile] = {}
        self.bilateral_matrix: np.ndarray = np.array([])
        self.elasticities: Dict[str, float] = {}
        self.meta: Dict[str, Any] = {}
        self._load_and_compile()

    def _load_and_compile(self) -> None:
        """加载基准跨国贸易数据并编译双边流动矩阵."""
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.meta = data.get("meta", {})
        self.elasticities = data.get("trade_elasticities", {})

        self.regions = []
        self.region_ids = []
        self.region_map = {}

        for r in data["regions"]:
            rid = r["region_id"]
            prof = RegionTradeProfile(
                region_id=rid,
                region_name_zh=r["region_name_zh"],
                region_name_en=r["region_name_en"],
                nominal_gdp_trillion=float(r["nominal_gdp_trillion_usd"]),
                gross_exports_trillion=float(r["gross_exports_trillion_usd"]),
                gross_imports_trillion=float(r["gross_imports_trillion_usd"]),
                net_exports_trillion=float(r["net_exports_trillion_usd"]),
                export_openness_pct=float(r["export_openness_pct"]),
                import_penetration_pct=float(r["import_penetration_pct"]),
                currency=r["currency"],
                trade_regime=r["trade_regime"],
            )
            self.regions.append(prof)
            self.region_ids.append(rid)
            self.region_map[rid] = prof

        n = len(self.region_ids)
        matrix = np.zeros((n, n), dtype=np.float64)
        flow_data = data.get("bilateral_trade_flows_matrix_trillion_usd", {})
        row_data = flow_data.get("rows_origin_exporters", {})

        for row_idx, rid in enumerate(self.region_ids):
            row_vals = row_data.get(rid, [0.0] * n)
            matrix[row_idx, :] = np.array(row_vals[:n], dtype=np.float64)

        self.bilateral_matrix = matrix

    def get_region_profiles(self) -> List[RegionTradeProfile]:
        """获取所有经济体对外贸易概况列表."""
        return self.regions

    def get_region_profile(self, region_id: str) -> Optional[RegionTradeProfile]:
        """根据区域代码获取经济体对外贸易档案."""
        return self.region_map.get(region_id.upper())

    def verify_global_trade_conservation(self) -> Dict[str, Any]:
        """核验全球贸易守恒律: 全球总出口 == 全球总进口, 全球净出口恒为零."""
        total_exports = float(np.sum(self.bilateral_matrix))
        row_sums = np.sum(self.bilateral_matrix, axis=1)  # 各国出口总计
        col_sums = np.sum(self.bilateral_matrix, axis=0)  # 各国进口总计

        net_exports = row_sums - col_sums
        sum_net_exports = float(np.sum(net_exports))

        is_conserved = abs(sum_net_exports) < 1e-4

        return {
            "total_world_exports_trillion": round(float(np.sum(row_sums)), 4),
            "total_world_imports_trillion": round(float(np.sum(col_sums)), 4),
            "world_net_exports_sum_trillion": round(sum_net_exports, 6),
            "is_trade_strictly_conserved": is_conserved,
            "region_balances": [
                {
                    "region_id": self.region_ids[i],
                    "exports_trillion": round(float(row_sums[i]), 3),
                    "imports_trillion": round(float(col_sums[i]), 3),
                    "net_exports_trillion": round(float(net_exports[i]), 3),
                }
                for i in range(len(self.region_ids))
            ]
        }

    def simulate_trade_and_fx_shock(
        self,
        # 1. 关税冲击 (Tariff Shock in Basis Points, 例如 500 bps = 5% 关税)
        tariff_shock_bps: float = 0.0,
        # 2. 汇率变动 (百分比, 例如 日元相对美元贬值 10% => +10.0)
        jpy_depreciation_pct: float = 0.0,
        # 3. 美国内需增量冲击 (万亿美元, 例如 美国消费激增带动进口)
        us_demand_shock_trillion: float = 0.0,
    ) -> Dict[str, Any]:
        """模拟跨国贸易关税、主要汇率重估及特定国家需求拉动的全球溢出效应.

        传导机制:
        - 关税增加会通过贸易摩擦弹性收缩双边贸易量;
        - 日元贬值将提升日本出口企业的日元营收换算利润与微观加价率弹性;
        - 美国内需扩张将按双边进口权重拉动日本、中国与欧盟的对美出口总额。
        """
        n = len(self.region_ids)
        sim_matrix = self.bilateral_matrix.copy()

        # 1. 关税收缩效应
        if abs(tariff_shock_bps) > 1e-4:
            tariff_pct = tariff_shock_bps / 100.0
            pass_through = self.elasticities.get("global_tariff_transmission_pass_through", 0.78)
            contraction_factor = max(0.5, 1.0 - (tariff_pct / 100.0) * pass_through)
            sim_matrix *= contraction_factor

        # 2. 美国内需激增对各出口国的边际拉动 (列 0 为美国进口)
        us_idx = self.region_ids.index("US") if "US" in self.region_ids else -1
        jp_idx = self.region_ids.index("JP") if "JP" in self.region_ids else -1

        if us_idx >= 0 and abs(us_demand_shock_trillion) > 1e-4:
            # 边际进口倾向约 15%~20%
            marginal_import_expansion = us_demand_shock_trillion * 0.18
            base_us_imports = np.sum(sim_matrix[:, us_idx])
            if base_us_imports > 1e-6:
                pull_ratio = 1.0 + (marginal_import_expansion / base_us_imports)
                for r in range(n):
                    if r != us_idx:
                        sim_matrix[r, us_idx] *= pull_ratio

        # 3. 日元汇率对外需与出口收入的弹性放大
        jpy_rev_multiplier = 1.0
        if jp_idx >= 0 and abs(jpy_depreciation_pct) > 1e-4:
            jpy_elasticity = self.elasticities.get("japanese_yen_depreciation_export_jpy_revenue_elasticity", 0.95)
            # 日元贬值对出口日元结算收入的扩张系数
            jpy_rev_multiplier = 1.0 + (jpy_depreciation_pct / 100.0) * jpy_elasticity

        # 重新核算各国出口与进口
        new_exports = np.sum(sim_matrix, axis=1)
        new_imports = np.sum(sim_matrix, axis=0)
        new_net_exports = new_exports - new_imports

        # 全球总贸易额
        total_trade = float(np.sum(sim_matrix))

        results_by_region = {}
        for idx, rid in enumerate(self.region_ids):
            base_exp = self.region_map[rid].gross_exports_trillion
            base_imp = self.region_map[rid].gross_imports_trillion
            cur_exp = float(new_exports[idx])
            cur_imp = float(new_imports[idx])
            cur_nx = float(new_net_exports[idx])

            delta_exp_pct = ((cur_exp - base_exp) / max(1e-6, base_exp)) * 100.0
            delta_imp_pct = ((cur_imp - base_imp) / max(1e-6, base_imp)) * 100.0

            results_by_region[rid] = {
                "region_id": rid,
                "name_zh": self.region_map[rid].region_name_zh,
                "base_exports_trillion": base_exp,
                "simulated_exports_trillion": round(cur_exp, 3),
                "export_growth_pct": round(delta_exp_pct, 2),
                "base_imports_trillion": base_imp,
                "simulated_imports_trillion": round(cur_imp, 3),
                "import_growth_pct": round(delta_imp_pct, 2),
                "net_exports_trillion": round(cur_nx, 3),
            }

        return {
            "total_simulated_world_gross_trade_trillion": round(total_trade, 3),
            "world_net_exports_balance_check_trillion": round(float(np.sum(new_net_exports)), 6),
            "is_global_trade_conserved": abs(float(np.sum(new_net_exports))) < 1e-4,
            "jpy_export_revenue_multiplier": round(jpy_rev_multiplier, 4),
            "region_trade_impacts": results_by_region,
        }
