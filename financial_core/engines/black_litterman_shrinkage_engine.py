# -*- coding: utf-8 -*-
"""基本面与动量权重转化器：Ledoit-Wolf 协方差收缩与 Black-Litterman 贝叶斯组合配置引擎 (black_litterman_shrinkage_engine.py).

遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，纯数学与统计推导，自包含矩阵代数解法器；
2. Ledoit-Wolf 线性协方差矩阵收缩 (Shrinkage Covariance)：
   - 解决小样本高维资产协方差矩阵奇异、病态与非正定问题；
   - 目标矩阵 F 采用等相关单因子结构 (Constant Correlation Target)；
   - 解析推导最优收缩强度 delta* in [0, 1]，保障逆矩阵绝对稳健正定；
3. Black-Litterman 贝叶斯后验期望收益整合：
   - 市场先验均衡超额收益 Pi = lambda * Sigma * w_mkt (反向优化，消除输入敏感性)；
   - 主观观点系统 (P, Q, Omega)：将客观基本面评分与动量多空观点平滑映射；
   - 贝叶斯后验期望收益 hat_mu 与后验协方差 Sigma_BL 闭式解析求解；
4. 投资组合最优权重生成与有限责任长多 (Long-Only) 及单票上限防抱团约束；
5. 全流程数值奇异保护与除零边界防御。
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Optional, Tuple


# ==========================================
# 纯净自包含轻量矩阵线性代数运算库
# ==========================================

def _mat_zeros(rows: int, cols: int) -> List[List[float]]:
    return [[0.0] * cols for _ in range(rows)]

def _mat_eye(n: int) -> List[List[float]]:
    m = _mat_zeros(n, n)
    for i in range(n):
        m[i][i] = 1.0
    return m

def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    r_a, c_a = len(a), len(a[0])
    r_b, c_b = len(b), len(b[0])
    if c_a != r_b:
        raise ValueError(f"矩阵乘法维度不匹配: ({r_a}x{c_a}) vs ({r_b}x{c_b})")
    out = _mat_zeros(r_a, c_b)
    for i in range(r_a):
        for k in range(c_a):
            if abs(a[i][k]) < 1e-15:
                continue
            for j in range(c_b):
                out[i][j] += a[i][k] * b[k][j]
    return out

def _mat_vec_mul(a: List[List[float]], v: List[float]) -> List[float]:
    r_a, c_a = len(a), len(a[0])
    if c_a != len(v):
        raise ValueError(f"矩阵向量乘法维度不匹配: ({r_a}x{c_a}) vs ({len(v)})")
    return [sum(a[i][j] * v[j] for j in range(c_a)) for i in range(r_a)]

def _mat_transpose(a: List[List[float]]) -> List[List[float]]:
    r, c = len(a), len(a[0])
    out = _mat_zeros(c, r)
    for i in range(r):
        for j in range(c):
            out[j][i] = a[i][j]
    return out

def _mat_add(a: List[List[float]], b: List[List[float]], scale_b: float = 1.0) -> List[List[float]]:
    r, c = len(a), len(a[0])
    out = _mat_zeros(r, c)
    for i in range(r):
        for j in range(c):
            out[i][j] = a[i][j] + scale_b * b[i][j]
    return out

def _mat_inv(matrix: List[List[float]]) -> List[List[float]]:
    """高斯-约当消元法 (带部分主元选取) 求解矩阵逆，内嵌正则化对角扰动防止奇异."""
    n = len(matrix)
    # 创建增广矩阵 [A | I]
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]

    # 对角线微弱正则化扰动保护 (Ridge Tikhonov)
    for i in range(n):
        aug[i][i] += 1e-8

    for col in range(n):
        # 寻找主元
        pivot_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                pivot_row = row

        if max_val < 1e-12:
            aug[col][col] += 1e-6  # 再次注入微弱对角扰动脱困

        # 交换行
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]

        # 归一化主行
        pivot = aug[col][col]
        for j in range(2 * n):
            aug[col][j] /= pivot

        # 消元其他行
        for row in range(n):
            if row != col:
                factor = aug[row][col]
                for j in range(2 * n):
                    aug[row][j] -= factor * aug[col][j]

    # 提取逆矩阵
    inv = [[aug[i][n + j] for j in range(n)] for i in range(n)]
    return inv


# ==========================================
# 业务数据契约
# ==========================================

@dataclass
class ShrinkageResult:
    """Ledoit-Wolf 协方差矩阵收缩契约."""
    optimal_shrinkage_intensity: float # 最优收缩强度 delta* (0.0=纯样本, 1.0=纯结构化)
    average_correlation: float         # 资产间平均相关系数
    is_shrunk: bool
    shrunk_covariance: List[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimal_shrinkage_intensity": self.optimal_shrinkage_intensity,
            "average_correlation": self.average_correlation,
            "is_shrunk": self.is_shrunk,
            "shrunk_covariance": self.shrunk_covariance,
        }


@dataclass
class BlackLittermanResult:
    """Black-Litterman 贝叶斯后验收益与配置权重契约."""
    tickers: List[str]
    prior_expected_returns: List[float]  # 市场先验均衡超额收益 Pi
    posterior_expected_returns: List[float] # BL 贝叶斯后验期望收益 hat_mu
    optimized_weights: Dict[str, float]  # 最终平滑优化长多组合权重 (和为 100%)
    active_tilts: Dict[str, float]       # 相对基准权重的偏离倾向 (Tilt)
    risk_aversion_lambda: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tickers": self.tickers,
            "prior_expected_returns": self.prior_expected_returns,
            "posterior_expected_returns": self.posterior_expected_returns,
            "optimized_weights": self.optimized_weights,
            "active_tilts": self.active_tilts,
            "risk_aversion_lambda": self.risk_aversion_lambda,
        }


class BlackLittermanShrinkageEngine:
    """Ledoit-Wolf 协方差收缩与 Black-Litterman 贝叶斯配置引擎."""

    def __init__(
        self,
        tau: float = 0.05,                  # 观点不确定性缩放标量 (一般取 0.025~0.05)
        default_risk_aversion: float = 2.8, # 市场平均相对风险厌恶系数 lambda
        max_single_weight: float = 0.25,    # 单票持仓硬性上限 (防止过度集中)
        annualization_factor: float = 252.0,
    ):
        self.tau = tau
        self.risk_aversion = default_risk_aversion
        self.max_single_weight = max_single_weight
        self.ann_factor = annualization_factor

    def compute_ledoit_wolf_shrinkage(
        self,
        returns_matrix: List[List[float]], # T x N (T 个交易日，N 只股票)
    ) -> ShrinkageResult:
        """Ledoit-Wolf 2004 线性协方差收缩算法，生成稳健正定协方差矩阵."""
        T = len(returns_matrix)
        N = len(returns_matrix[0])

        if T < 10 or N < 2:
            raise ValueError(f"协方差收缩需要至少 10 个时间步长与 2 只资产，当前: T={T}, N={N}")

        # 1. 计算样本均值与去均值收益矩阵
        means = [sum(returns_matrix[t][i] for t in range(T)) / T for i in range(N)]
        X = [[returns_matrix[t][i] - means[i] for i in range(N)] for t in range(T)]

        # 2. 计算样本协方差矩阵 S
        S = _mat_zeros(N, N)
        for i in range(N):
            for j in range(i, N):
                cov = sum(X[t][i] * X[t][j] for t in range(T)) / (T - 1)
                S[i][j] = cov
                S[j][i] = cov

        # 3. 计算等相关目标矩阵 F (Constant Correlation Target)
        stds = [math.sqrt(max(S[i][i], 1e-8)) for i in range(N)]
        corr_sum = 0.0
        corr_count = 0
        for i in range(N):
            for j in range(i + 1, N):
                r_ij = S[i][j] / (stds[i] * stds[j])
                corr_sum += r_ij
                corr_count += 1
        r_bar = corr_sum / max(corr_count, 1)

        F = _mat_zeros(N, N)
        for i in range(N):
            for j in range(N):
                if i == j:
                    F[i][j] = S[i][i]
                else:
                    F[i][j] = r_bar * stds[i] * stds[j]

        # 4. 统计估计最优收缩强度 delta*
        # pi_hat (协方差元素渐近渐变和)
        pi_mat = _mat_zeros(N, N)
        for i in range(N):
            for j in range(N):
                pi_ij = sum(((X[t][i] * X[t][j]) - S[i][j]) ** 2 for t in range(T)) / T
                pi_mat[i][j] = pi_ij
        pi_hat = sum(sum(row) for row in pi_mat)

        # gamma_hat (样本 S 与目标 F 之间的弗罗贝尼乌斯范数平方)
        gamma_hat = sum((S[i][j] - F[i][j]) ** 2 for i in range(N) for j in range(N))

        # rho_hat
        rho_hat = 0.0
        for i in range(N):
            for j in range(N):
                if i == j:
                    rho_hat += pi_mat[i][i]
                else:
                    # 近似渐近估计
                    theta_ii_ij = sum(((X[t][i]**2 - S[i][i]) * (X[t][i]*X[t][j] - S[i][j])) for t in range(T)) / T
                    theta_jj_ij = sum(((X[t][j]**2 - S[j][j]) * (X[t][i]*X[t][j] - S[i][j])) for t in range(T)) / T
                    rho_hat += (r_bar / 2.0) * (
                        stds[j]/stds[i] * theta_ii_ij + stds[i]/stds[j] * theta_jj_ij
                    )

        # 最优收缩强度 kappa
        kappa = (pi_hat - rho_hat) / max(gamma_hat, 1e-8)
        delta_star = max(0.0, min(1.0, kappa / T))

        # 5. 组合收缩矩阵 Sigma_shrunk = delta* * F + (1 - delta*) * S
        shrunk_cov = _mat_add(
            [[F[i][j] * delta_star for j in range(N)] for i in range(N)],
            [[(1.0 - delta_star) * S[i][j] for j in range(N)] for i in range(N)]
        )

        return ShrinkageResult(
            optimal_shrinkage_intensity=round(delta_star, 4),
            average_correlation=round(r_bar, 4),
            is_shrunk=delta_star > 0.01,
            shrunk_covariance=shrunk_cov,
        )

    def optimize_black_litterman(
        self,
        tickers: List[str],
        covariance_matrix: List[List[float]],
        market_benchmark_weights: List[float],
        views_dict: Dict[str, float],         # 标的观点超额收益字典: {"NVDA": 0.15, "AAPL": -0.05}
        views_confidence: Optional[Dict[str, float]] = None, # 观点置信度 (0.1 ~ 1.0)
    ) -> BlackLittermanResult:
        """运行 Black-Litterman 贝叶斯后验均衡模型，输出平滑资产配置权重."""
        N = len(tickers)
        if len(market_benchmark_weights) != N:
            raise ValueError(f"基准权重维度 ({len(market_benchmark_weights)}) 与标的数量 ({N}) 不一致")

        # 归一化市场基准权重
        w_mkt_sum = sum(market_benchmark_weights) or 1.0
        w_mkt = [w / w_mkt_sum for w in market_benchmark_weights]

        # 1. 市场先验均衡超额收益: Pi = lambda * Sigma * w_mkt
        sigma = covariance_matrix
        pi_prior = _mat_vec_mul(sigma, w_mkt)
        pi_prior = [self.risk_aversion * p for p in pi_prior]

        # 2. 构建投资者观点矩阵 P 与观点向量 Q
        active_views = [(t, val) for t, val in views_dict.items() if t in tickers]
        K = len(active_views)

        if K == 0:
            # 无主观观点时，BL 贝叶斯后验完全退化收敛为市场先验权重
            opt_w = {tickers[i]: round(w_mkt[i], 4) for i in range(N)}
            tilts = {tickers[i]: 0.0 for i in range(N)}
            return BlackLittermanResult(
                tickers=tickers,
                prior_expected_returns=[round(p, 4) for p in pi_prior],
                posterior_expected_returns=[round(p, 4) for p in pi_prior],
                optimized_weights=opt_w,
                active_tilts=tilts,
                risk_aversion_lambda=self.risk_aversion,
            )

        P = _mat_zeros(K, N)
        Q = [0.0] * K
        conf = views_confidence or {}

        for k_idx, (tk, val) in enumerate(active_views):
            col_idx = tickers.index(tk)
            P[k_idx][col_idx] = 1.0
            Q[k_idx] = val

        # 3. 构造观点不确定性协方差 Omega (采用 Idzorek 对角设定: Omega = diag(P * (tau * Sigma) * P^T))
        tau_sigma = [[self.tau * sigma[i][j] for j in range(N)] for i in range(N)]
        P_tau_sigma = _mat_mul(P, tau_sigma)
        P_tau_sigma_Pt = _mat_mul(P_tau_sigma, _mat_transpose(P))

        Omega = _mat_zeros(K, K)
        for k_idx in range(K):
            tk = active_views[k_idx][0]
            c = conf.get(tk, 0.5)  # 默认 50% 置信度
            uncertainty_scalar = (1.0 - c) / max(c, 1e-4)
            Omega[k_idx][k_idx] = max(P_tau_sigma_Pt[k_idx][k_idx] * uncertainty_scalar, 1e-6)

        # 4. 贝叶斯后验期望收益求解 (Sherman-Morrison-Woodbury 形式):
        # hat_mu = Pi + tau * Sigma * P^T * [P * (tau * Sigma) * P^T + Omega]^-1 * (Q - P * Pi)
        P_pi = _mat_vec_mul(P, pi_prior)
        view_excess = [Q[k] - P_pi[k] for k in range(K)]

        M = _mat_add(P_tau_sigma_Pt, Omega)
        M_inv = _mat_inv(M)

        Pt = _mat_transpose(P)
        tau_sigma_Pt = _mat_mul(tau_sigma, Pt)
        weight_adjust_mat = _mat_mul(tau_sigma_Pt, M_inv)

        delta_mu = _mat_vec_mul(weight_adjust_mat, view_excess)
        hat_mu = [pi_prior[i] + delta_mu[i] for i in range(N)]

        # 5. 后验主动偏离 (Active Tilts) 与组合权重计算
        # 在 Black-Litterman 经典框架中，最优资产权重为基准组合权重 w_mkt 加上由观点超额收益驱动的主动偏离:
        # delta_w = (1 / lambda) * Sigma_inv * (hat_mu - Pi)
        sigma_inv = _mat_inv(sigma)
        raw_tilts = _mat_vec_mul(sigma_inv, delta_mu)
        raw_tilts = [t / self.risk_aversion for t in raw_tilts]

        # 均值中心化保证主动偏离为零和博弈 (sum(delta_w) == 0.0)
        mean_tilt = sum(raw_tilts) / N
        centered_tilts = [t - mean_tilt for t in raw_tilts]

        # 基础未截断权重: w_mkt + centered_tilts
        eff_max_w = max(self.max_single_weight, 1.0 / N)
        w = [w_mkt[i] + centered_tilts[i] for i in range(N)]

        # 6. 长多约束 (Long-Only, >= 0.0) 与单票上限 (<= eff_max_w) 迭代平滑重分配
        for _ in range(10):
            excess = 0.0
            for i in range(N):
                if w[i] < 0.0:
                    excess += w[i]
                    w[i] = 0.0
                elif w[i] > eff_max_w:
                    excess += (w[i] - eff_max_w)
                    w[i] = eff_max_w

            if abs(excess) < 1e-6:
                break

            uncapped = [i for i in range(N) if 0.0 < w[i] < eff_max_w]
            if not uncapped:
                uncapped = [i for i in range(N) if w[i] < eff_max_w]
            u_sum = sum(w_mkt[i] for i in uncapped) or 1.0
            for i in uncapped:
                w[i] += excess * (w_mkt[i] / u_sum)

        tot = sum(w) or 1.0
        final_weights = {tickers[i]: round(w[i] / tot, 4) for i in range(N)}
        tilts = {tickers[i]: round(final_weights[tickers[i]] - w_mkt[i], 4) for i in range(N)}

        return BlackLittermanResult(
            tickers=tickers,
            prior_expected_returns=[round(p, 4) for p in pi_prior],
            posterior_expected_returns=[round(m, 4) for m in hat_mu],
            optimized_weights=final_weights,
            active_tilts=tilts,
            risk_aversion_lambda=self.risk_aversion,
        )
