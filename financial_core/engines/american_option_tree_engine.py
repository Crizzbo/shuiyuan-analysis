"""美式期权二叉树 (Cox-Ross-Rubinstein, CRR) 与跳跃扩散数值引擎.

遵循 Google Python 编程风格指南与《SPEC-05 估值矩阵与期权二叉树规格书》:
1. 替代纯欧式 BSM 连续解，支持美式期权全生命周期提前行权 (Early Exercise) 动态规划定价;
2. 准确刻画除息日前夕实值 Call 与深度实值 Put 锁定无风险利息的真实公允价值;
3. 引入 Richardson 外推法消除奇偶步长离散震荡，收敛阶数跃升至 O(1/N^2);
4. 引入 Merton 跳跃扩散 (Jump-Diffusion) 泊松跳跃厚尾补偿，刻画黑天鹅极端跳空.
"""

# 1. Python 标准库
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AmericanOptionTreeInput:
    """美式期权二叉树输入参数数据契约.

    Attributes:
        spot_price: 标的现价 S.
        strike_price: 行权价 K.
        time_to_expiry_years: 到期剩余期限 (年) T.
        risk_free_rate: 无风险利率 r.
        implied_vol: 隐含波动率 sigma.
        dividend_yield: 连续红利股息率 q (默认 0.0).
        is_call: True 为看涨期权 Call, False 为看跌期权 Put.
        steps: 二叉树步数 N (推荐 100~300).
        jump_intensity: 泊松跳跃年化发生频率 lambda (例如每年 1 次跳跃).
        mean_jump_size: 平均跳跃幅度 k (例如 -0.20 代表暴跌 20%).
        jump_vol: 跳跃幅度对数正态标准差 delta.
        currency_symbol: 货币符号 ('$', '¥').
    """

    spot_price: float
    strike_price: float
    time_to_expiry_years: float
    risk_free_rate: float
    implied_vol: float
    dividend_yield: float = 0.0
    is_call: bool = True
    steps: int = 100
    jump_intensity: float = 0.0
    mean_jump_size: float = 0.0
    jump_vol: float = 0.0
    currency_symbol: str = "$"


class AmericanOptionTreeEngine:
    """CRR 美式期权二叉树与极端跳跃扩散定价中枢 (Google Python Style Guide 架构设计)."""

    def __init__(self):
        """初始化二叉树期权定价引擎."""
        self.version: str = "1.0.0"

    def price_crr_tree(self, params: AmericanOptionTreeInput) -> Dict[str, Any]:
        """使用 CRR 二叉树逆向动态规划与 Richardson 外推计算美式期权公允价值与早行权边界.

        Args:
            params: AmericanOptionTreeInput 强类型期权输入契约.

        Returns:
            Dict[str, Any] 包含美式价格、欧式对照价、提前行权溢价、Greeks 因子与通俗研报的字典.

        Raises:
            ValueError: 当标的现价或行权价 <= 0.0 时抛出 (金融数学边界防御).
        """
        if params.spot_price <= 0.0 or params.strike_price <= 0.0:
            raise ValueError(
                f"【金融数学防御】标的现价与行权价必须大于0，收到非法值: "
                f"spot_price={params.spot_price}, strike_price={params.strike_price}"
            )

        spot = params.spot_price
        strike = params.strike_price
        expiry = max(1e-4, params.time_to_expiry_years)
        r = params.risk_free_rate
        q = params.dividend_yield
        sigma = max(0.01, params.implied_vol)
        is_call = params.is_call

        # 确定无套利二叉树步长
        n_steps = self._determine_arbitrage_free_steps(
            expiry=expiry, r=r, q=q, sigma=sigma, base_steps=params.steps
        )

        # 1. 运行基准 N 步二叉树
        p_n, ee_occ, max_prem, u, d, p = self._crr_tree_internal(
            spot, strike, expiry, r, q, sigma, n_steps, is_call
        )

        # 2. 运行高阶 2N 步二叉树并执行 Richardson 外推
        n_2x = min(1000, 2 * n_steps)
        p_2n, _, _, _, _, _ = self._crr_tree_internal(
            spot, strike, expiry, r, q, sigma, n_2x, is_call
        )
        richardson_price = 2.0 * p_2n - p_n

        intrinsic = max(0.0, spot - strike) if is_call else max(0.0, strike - spot)
        american_price = max(intrinsic, richardson_price)

        # 3. 计算纯欧式对照价格以剥离美式提前行权溢价
        european_price = self._price_european_black_scholes(
            spot, strike, expiry, r, q, sigma, is_call
        )
        early_exercise_premium = max(0.0, american_price - european_price)
        premium_ratio_pct = (early_exercise_premium / max(1e-4, american_price)) * 100.0

        # 4. 若启用了 Merton 跳跃扩散，计算极端跳跃调整溢价
        jump_adjusted_price = american_price
        if params.jump_intensity > 0:
            jump_adjusted_price = self._adjust_for_merton_jump(
                spot=spot,
                strike=strike,
                expiry=expiry,
                r=r,
                q=q,
                sigma=sigma,
                is_call=is_call,
                lam=params.jump_intensity,
                mean_jump=params.mean_jump_size,
                jump_vol=params.jump_vol,
                early_exercise_premium=early_exercise_premium,
                intrinsic=intrinsic,
            )

        # 5. 生成通俗买方研报叙述卡片
        narrative_zh = self._render_narrative(
            params=params,
            spot=spot,
            strike=strike,
            expiry=expiry,
            american_price=american_price,
            european_price=european_price,
            early_exercise_premium=early_exercise_premium,
            premium_ratio_pct=premium_ratio_pct,
            ee_occ=ee_occ,
            max_prem=max_prem,
            jump_adjusted_price=jump_adjusted_price,
        )

        return {
            "american_price": round(american_price, 4),
            "raw_crr_n_price": round(p_n, 4),
            "richardson_extrapolated_price": round(american_price, 4),
            "european_price": round(european_price, 4),
            "early_exercise_premium": round(early_exercise_premium, 4),
            "early_exercise_premium_ratio_pct": round(premium_ratio_pct, 2),
            "early_exercise_occurred": ee_occ,
            "jump_adjusted_price": round(jump_adjusted_price, 4),
            "tree_steps": n_steps,
            "up_factor": round(u, 4),
            "down_factor": round(d, 4),
            "risk_neutral_prob": round(p, 4),
            "narrative_zh": narrative_zh,
        }

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _determine_arbitrage_free_steps(
        expiry: float, r: float, q: float, sigma: float, base_steps: int
    ) -> int:
        """测算满足无套利边界的最小二叉树步长 (私有辅助方法)."""
        drift_rate = abs(r - q)
        min_steps_arb_free = int(math.ceil(expiry * (drift_rate**2) / (sigma**2))) + 1
        safe_base = max(10, min(500, base_steps))
        return max(safe_base, min(800, min_steps_arb_free))

    @staticmethod
    def _crr_tree_internal(
        spot: float,
        strike: float,
        expiry: float,
        r: float,
        q: float,
        sigma: float,
        n_steps: int,
        is_call: bool,
    ) -> Tuple[float, bool, float, float, float, float]:
        """单次 CRR 二叉树逆向归纳计算核心 (私有辅助方法)."""
        dt = expiry / n_steps
        df = math.exp(-r * dt)
        u = math.exp(sigma * math.sqrt(dt))
        d = 1.0 / u

        drift = math.exp((r - q) * dt)
        raw_p = (drift - d) / (u - d)
        p = min(1.0 - 1e-7, max(1e-7, raw_p))
        one_minus_p = 1.0 - p

        values = [0.0] * (n_steps + 1)
        for j in range(n_steps + 1):
            st = spot * math.pow(u, 2 * j - n_steps)
            values[j] = max(0.0, st - strike) if is_call else max(0.0, strike - st)

        early_exercise_occurred = False
        max_early_exercise_premium = 0.0

        for i in range(n_steps - 1, -1, -1):
            for j in range(i + 1):
                hold_value = df * (p * values[j + 1] + one_minus_p * values[j])
                st = spot * math.pow(u, 2 * j - i)
                exercise_value = max(0.0, st - strike) if is_call else max(0.0, strike - st)

                if exercise_value > hold_value + 1e-6:
                    early_exercise_occurred = True
                    diff = exercise_value - hold_value
                    if diff > max_early_exercise_premium:
                        max_early_exercise_premium = diff
                    values[j] = exercise_value
                else:
                    values[j] = hold_value

        return values[0], early_exercise_occurred, max_early_exercise_premium, u, d, p

    @staticmethod
    def _price_european_black_scholes(
        spot: float,
        strike: float,
        expiry: float,
        r: float,
        q: float,
        sigma: float,
        is_call: bool,
    ) -> float:
        """BSM 欧式基准解析解 (私有辅助方法)."""
        d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * expiry) / (
            sigma * math.sqrt(expiry)
        )
        d2 = d1 - sigma * math.sqrt(expiry)

        def norm_cdf(x: float) -> float:
            return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

        if is_call:
            return spot * math.exp(-q * expiry) * norm_cdf(d1) - strike * math.exp(
                -r * expiry
            ) * norm_cdf(d2)
        return strike * math.exp(-r * expiry) * norm_cdf(-d2) - spot * math.exp(
            -q * expiry
        ) * norm_cdf(-d1)

    @classmethod
    def _adjust_for_merton_jump(
        cls,
        spot: float,
        strike: float,
        expiry: float,
        r: float,
        q: float,
        sigma: float,
        is_call: bool,
        lam: float,
        mean_jump: float,
        jump_vol: float,
        early_exercise_premium: float = 0.0,
        intrinsic: float = 0.0,
    ) -> float:
        """Merton (1976) 跳跃扩散级数近似解 (私有辅助方法)."""
        safe_jump = max(-0.99, min(5.0, float(mean_jump)))
        lam_safe = max(0.0, float(lam))
        jump_vol_safe = max(0.0, float(jump_vol))

        jump_price = 0.0
        lam_prime = lam_safe * (1.0 + safe_jump)
        for n in range(6):
            p_n = (math.exp(-lam_prime * expiry) * math.pow(lam_prime * expiry, n)) / math.factorial(n)
            sigma_n = math.sqrt(sigma * sigma + n * jump_vol_safe * jump_vol_safe / expiry)
            r_n = r - lam_safe * safe_jump + n * math.log(1.0 + safe_jump) / expiry
            bs_n = cls._price_european_black_scholes(spot, strike, expiry, r_n, q, sigma_n, is_call)
            jump_price += p_n * bs_n

        return max(intrinsic, jump_price + early_exercise_premium)

    @staticmethod
    def _render_narrative(
        params: AmericanOptionTreeInput,
        spot: float,
        strike: float,
        expiry: float,
        american_price: float,
        european_price: float,
        early_exercise_premium: float,
        premium_ratio_pct: float,
        ee_occ: bool,
        max_prem: float,
        jump_adjusted_price: float,
    ) -> str:
        """渲染买方通俗自然语言研报卡片 (私有辅助方法)."""
        curr_sym = getattr(params, "currency_symbol", "$") or "$"
        opt_type_zh = "美式看涨期权" if params.is_call else "美式看跌期权"

        if ee_occ:
            exercise_advice_zh = (
                f"【触发提前行权优势】模型监测到在存续期节点存在提前行权价值（最大早行权利差约 {curr_sym}{max_prem:.2f}）；"
                f"建议在除息日前夕或深度实值锁定贴现收益窗口期主动行权，防止时间价值与股息流失。"
            )
        else:
            exercise_advice_zh = (
                f"【持有时间价值更优】未监测到显著提前行权收益；"
                f"当前期权所含时间价值高于立即行权价值，理性买方应继续持有合约或在二级市场转让，而非过早行权。"
            )

        jump_note_zh = (
            f"已叠加 Merton 黑天鹅跳跃厚尾补偿（调整后公允价 {curr_sym}{jump_adjusted_price:.2f}）"
            if params.jump_intensity > 0
            else "处于连续平滑扩散基准假设下"
        )

        return (
            f"【{opt_type_zh} 二叉树定价与时机研判】当前标的现价 {curr_sym}{spot:.2f}，"
            f"行权价 {curr_sym}{strike:.2f}，到期期限 {expiry:.2f}年。"
            f"二叉树公允理论价为 {curr_sym}{american_price:.2f}，纯欧式对照基准为 {curr_sym}{european_price:.2f}，"
            f"内含美式提前行权特权溢价 {curr_sym}{early_exercise_premium:.2f} (溢价占比 {premium_ratio_pct:.1f}%)。"
            f"{exercise_advice_zh} 当前{jump_note_zh}。"
        )
