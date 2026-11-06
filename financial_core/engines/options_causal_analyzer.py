"""期权投资因果链量化推导与全周期损益分析引擎 (Options Causal Analyzer).

遵循 Google Python 编程风格指南与《SPEC-08 期权全周期因果分析与仓位风控引擎设计书》，
彻底杜绝“跳过现价与期权盘口直接给出预期收益”的跨级因果断裂。

严格遵循五级因果推导链条：
1. 【前项 1：标的物现价与时效核验 (Spot & Session Gate)】：
   前置输入标的物现价、采样时间戳与交易时段，严禁未核验时效；
2. 【前项 2：期权盘口与合约属性 (Contract & Premium)】：
   输入行权价 K、到期日与剩余交易天数、期权类型 (Call/Put)、实际买入权利金；
3. 【中项 1：期权性质与时间价值拆解 (Moneyness & Time Value)】：
   判定实值 (ITM) / 平价 (ATM) / 虚值 (OTM)，拆解内在价值与纯时间价值；
4. 【中项 2：保本损益临界点与归零风险 (Break-Even & Zero Risk)】：
   计算到期保本点、标的股票所需涨跌幅与虚值到期归零警示；
5. 【后项：情景到期损益分布与四分之一凯利期权风控 (Payoff & Quarter-Kelly)】：
   基于标的三态情景（悲观/基准/乐观）精确核算到期行权净损益与回报倍数，
   输出四分之一凯利权利金绝对风控配置上限（封顶 <= 2.0% 总资金）。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OptionContractInput:
    """期权合约前项真实输入事实.

    Attributes:
        underlying_ticker: 标的股票代码 (如 NVDA 或 7203.T).
        underlying_spot_price: 标的股票当前最新成交现价 (大于 0).
        spot_quote_timestamp: 行情采样时间戳 (ISO-8601 格式).
        market_session: 交易时段 (pre_market, regular_trading, after_hours, previous_close).
        strike_price: 期权合约行权价 (大于 0).
        option_type: 期权合约类型，仅限 "call" 或 "put".
        days_to_expiration: 距离到期日剩余天数 (DTE, 大于等于 0).
        market_premium: 实际需支付的权利金买入价格 (大于 0).
        contract_multiplier: 合约乘数 (美股美式期权通常为 100 股/张).
        risk_free_rate: 无风险基准年化利率 (如 0.044 代表 4.40%).
        implied_volatility: 盘口隐含波动率 (IV, 如 0.55 代表 55%).
        market: 交易市场 ("US" 或 "JP"，未指定时按代码自适应推导).
    """

    underlying_ticker: str
    underlying_spot_price: float
    spot_quote_timestamp: str
    market_session: str
    strike_price: float
    option_type: str
    days_to_expiration: int
    market_premium: float
    contract_multiplier: int = 100
    risk_free_rate: float = 0.0440
    implied_volatility: Optional[float] = None
    market: Optional[str] = None


@dataclass(frozen=True)
class UnderlyingScenarios:
    """标的股票在期权到期时的多情景价格分布假设 (概率严格守恒).

    Attributes:
        bear_price: 悲观情景价格 (跌破支撑或退守资产重估底线).
        bear_prob: 悲观情景发生概率 (在 0.0 至 1.0 之间).
        base_price: 基准中枢价格 (基准业务兑现公允内在价值).
        base_prob: 基准情景发生概率 (在 0.0 至 1.0 之间).
        bull_price: 乐观爆发价格 (催化剂放量或行业红利爆发).
        bull_prob: 乐观情景发生概率 (在 0.0 至 1.0 之间).
    """

    bear_price: float
    bear_prob: float
    base_price: float
    base_prob: float
    bull_price: float
    bull_prob: float


@dataclass(frozen=True)
class OptionAnalysisResult:
    """期权因果链完整推导分析结果.

    包含合约档案、中项性质拆解、到期三态损益分布、期望回报与仓位建议.
    """

    underlying_ticker: str
    underlying_spot_price: float
    market_session: str
    quote_freshness_desc: str
    strike_price: float
    option_type: str
    market_premium: float
    days_to_expiration: int

    # 中项推导
    moneyness_status: str
    intrinsic_value: float
    time_value: float
    time_value_ratio: float
    break_even_price: float
    required_spot_move_pct: float
    zero_loss_risk_desc: str

    # 各情景到期损益
    bear_payoff_per_share: float
    bear_return_pct: float
    base_payoff_per_share: float
    base_return_pct: float
    bull_payoff_per_share: float
    bull_return_pct: float

    # 期望与风控
    expected_profit_per_share: float
    expected_return_pct: float
    win_probability: float
    odds_b: float
    quarter_kelly_capital_pct: float
    verdict: str
    rationale_zh: str
    narrative_zh: str = ""
    verdict_zh: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """将期权分析结果序列化为符合买方研报展示规范的强类型字典.

        Returns:
            包含合约信息、因果拆解、三态损益与配置决策的结构化字典.
        """
        ticker_upper = self.underlying_ticker.upper()
        is_jp = (
            ticker_upper.endswith(".T")
            or ticker_upper.endswith(".JP")
            or (ticker_upper.isdigit() and len(ticker_upper) == 4)
        )
        curr = "¥" if is_jp else "$"
        return {
            "contract_profile": {
                "ticker": self.underlying_ticker,
                "spot_price": f"{curr}{self.underlying_spot_price:.2f}",
                "market_session": self.market_session,
                "freshness": self.quote_freshness_desc,
                "strike_price": f"{curr}{self.strike_price:.2f}",
                "option_type": self.option_type.upper(),
                "market_premium": f"{curr}{self.market_premium:.2f}",
                "days_to_expiration": f"{self.days_to_expiration} 天",
            },
            "causal_breakdown": {
                "moneyness": self.moneyness_status,
                "intrinsic_value": f"{curr}{self.intrinsic_value:.2f}",
                "time_value": f"{curr}{self.time_value:.2f}",
                "time_value_ratio": f"{self.time_value_ratio * 100:.1f}%",
                "break_even_price": f"{curr}{self.break_even_price:.2f}",
                "required_underlying_move": f"{self.required_spot_move_pct:+.2f}%",
                "zero_risk_warning": self.zero_loss_risk_desc,
            },
            "expiry_scenario_payoffs": {
                "bear_case": {
                    "net_profit_per_share": f"{curr}{self.bear_payoff_per_share:+.2f}",
                    "return_pct": f"{self.bear_return_pct:+.1f}%",
                },
                "base_case": {
                    "net_profit_per_share": f"{curr}{self.base_payoff_per_share:+.2f}",
                    "return_pct": f"{self.base_return_pct:+.1f}%",
                },
                "bull_case": {
                    "net_profit_per_share": f"{curr}{self.bull_payoff_per_share:+.2f}",
                    "return_pct": f"{self.bull_return_pct:+.1f}%",
                },
            },
            "decision_and_allocation": {
                "expected_profit_per_share": f"{curr}{self.expected_profit_per_share:+.2f}",
                "expected_return_pct": f"{self.expected_return_pct:+.2f}%",
                "win_probability": f"{self.win_probability * 100:.1f}%",
                "win_loss_odds": round(self.odds_b, 2),
                "quarter_kelly_capital_pct": f"{self.quarter_kelly_capital_pct:.2f}%",
                "verdict": self.verdict,
                "verdict_zh": self.verdict_zh or self.verdict,
                "rationale": self.rationale_zh,
                "narrative_zh": self.narrative_zh,
            },
            "narrative_zh": self.narrative_zh,
        }


class OptionsCausalAnalyzer:
    """期权因果链量化分析器 (遵循 Google Python Style Guide 架构设计)."""

    @classmethod
    def analyze_option(
        cls,
        contract: OptionContractInput,
        scenarios: UnderlyingScenarios,
        current_time_iso: Optional[str] = None,
        max_quote_staleness_hours: float = 24.0,
    ) -> OptionAnalysisResult:
        """执行端到端五级因果推导，杜绝跨级臆断预期收益.

        Args:
            contract: 期权合约前项真实输入事实对象.
            scenarios: 标的股票到期三态价格分布假设 (悲观/基准/乐观).
            current_time_iso: 当前基准时间戳 (ISO 格式，留空则自动取当前 UTC 时间).
            max_quote_staleness_hours: 行情允许的最大滞后小时数 (默认 24.0 小时).

        Returns:
            OptionAnalysisResult 全息分析结论对象.

        Raises:
            ValueError: 当行情时间戳非法、超期滞后、概率不守恒、期权类型非法或权利金小于等于 0 时抛出.
        """
        # 1. 验证时效性门禁
        freshness_label = cls._verify_quote_freshness(
            contract=contract,
            current_time_iso=current_time_iso,
            max_staleness_hours=max_quote_staleness_hours,
        )

        # 2. 校验情景概率守恒
        cls._validate_scenario_probabilities(scenarios)

        # 3. 提取并清洗合约关键要素
        opt_type = contract.option_type.lower()
        if opt_type not in ("call", "put"):
            raise ValueError("option_type 必须为 'call' 或 'put'")
        if contract.market_premium <= 0:
            raise ValueError("期权买入权利金必须大于 0")

        ticker_upper = contract.underlying_ticker.upper()
        market_upper = (contract.market or "").upper()
        is_jp = (
            market_upper == "JP"
            or ticker_upper.endswith(".T")
            or ticker_upper.endswith(".JP")
            or (ticker_upper.isdigit() and len(ticker_upper) == 4)
        )
        curr_sym = "¥" if is_jp else "$"

        spot = contract.underlying_spot_price
        safe_spot = max(0.01, spot)
        strike = contract.strike_price
        premium = contract.market_premium

        # 4. 中项推导：实虚值属性、内在价值与时间价值拆解
        moneyness, intrinsic, time_val, tv_ratio, break_even, req_move_pct, zero_warning = (
            cls._calculate_moneyness_and_break_even(
                spot=spot,
                safe_spot=safe_spot,
                strike=strike,
                premium=premium,
                opt_type=opt_type,
                curr_sym=curr_sym,
            )
        )

        # 5. 后项情景到期损益与收益率推导
        bear_net, bear_ret = cls._calc_payoff(scenarios.bear_price, strike, premium, opt_type)
        base_net, base_ret = cls._calc_payoff(scenarios.base_price, strike, premium, opt_type)
        bull_net, bull_ret = cls._calc_payoff(scenarios.bull_price, strike, premium, opt_type)

        # 6. 数学期望、胜率与盈亏赔率
        exp_profit, exp_return_pct, win_prob, odds_b = cls._compute_expectation_and_odds(
            scenarios=scenarios,
            bear_net=bear_net,
            base_net=base_net,
            bull_net=bull_net,
            premium=premium,
        )

        # 7. 四分之一凯利风控与买方通俗决策研判
        rec_kelly_pct, verdict, verdict_zh, rationale, narrative_zh = (
            cls._determine_verdict_and_kelly(
                contract=contract,
                scenarios=scenarios,
                opt_type=opt_type,
                spot=spot,
                strike=strike,
                premium=premium,
                intrinsic=intrinsic,
                time_val=time_val,
                tv_ratio=tv_ratio,
                break_even=break_even,
                req_move_pct=req_move_pct,
                moneyness=moneyness,
                bull_ret=bull_ret,
                exp_profit=exp_profit,
                exp_return_pct=exp_return_pct,
                win_prob=win_prob,
                odds_b=odds_b,
                curr_sym=curr_sym,
                freshness_label=freshness_label,
            )
        )

        return OptionAnalysisResult(
            underlying_ticker=contract.underlying_ticker,
            underlying_spot_price=spot,
            market_session=contract.market_session,
            quote_freshness_desc=freshness_label,
            strike_price=strike,
            option_type=opt_type,
            market_premium=premium,
            days_to_expiration=contract.days_to_expiration,
            moneyness_status=moneyness,
            intrinsic_value=round(intrinsic, 3),
            time_value=round(time_val, 3),
            time_value_ratio=round(tv_ratio, 4),
            break_even_price=round(break_even, 3),
            required_spot_move_pct=round(req_move_pct, 2),
            zero_loss_risk_desc=zero_warning,
            bear_payoff_per_share=bear_net,
            bear_return_pct=bear_ret,
            base_payoff_per_share=base_net,
            base_return_pct=base_ret,
            bull_payoff_per_share=bull_net,
            bull_return_pct=bull_ret,
            expected_profit_per_share=round(exp_profit, 3),
            expected_return_pct=round(exp_return_pct, 2),
            win_probability=round(win_prob, 4),
            odds_b=round(odds_b, 3),
            quarter_kelly_capital_pct=rec_kelly_pct,
            verdict=verdict,
            rationale_zh=rationale,
            narrative_zh=narrative_zh,
            verdict_zh=verdict_zh,
        )

    @classmethod
    def _verify_quote_freshness(
        cls,
        contract: OptionContractInput,
        current_time_iso: Optional[str],
        max_staleness_hours: float,
    ) -> str:
        """核验标的现价时效性门禁 (私有辅助方法)."""
        now_dt = (
            datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
            if current_time_iso
            else datetime.now(timezone.utc)
        )
        try:
            q_dt = datetime.fromisoformat(
                contract.spot_quote_timestamp.replace("Z", "+00:00")
            )
        except Exception as err:
            raise ValueError(
                f"行情时间戳格式非法: {contract.spot_quote_timestamp}"
            ) from err

        age_hours = (now_dt - q_dt).total_seconds() / 3600.0
        if age_hours > max_staleness_hours:
            raise ValueError(
                f"【行情时效硬约束阻断】标的 {contract.underlying_ticker} 行情已滞后 "
                f"{age_hours:.1f} 小时，严禁使用过时价格推演期权！"
            )

        if q_dt.date() == now_dt.date():
            return f"当日最新行情 (时差 {age_hours:.1f}h)"
        return f"前一交易日基准 (时差 {age_hours:.1f}h)"

    @classmethod
    def _validate_scenario_probabilities(cls, scenarios: UnderlyingScenarios) -> None:
        """校验情景概率之和守恒 (私有辅助方法)."""
        total_p = scenarios.bear_prob + scenarios.base_prob + scenarios.bull_prob
        if abs(total_p - 1.0) > 1e-4:
            raise ValueError(f"情景概率之和必须等于 1.0，当前和为 {total_p:.4f}")

    @classmethod
    def _calculate_moneyness_and_break_even(
        cls,
        spot: float,
        safe_spot: float,
        strike: float,
        premium: float,
        opt_type: str,
        curr_sym: str,
    ) -> Tuple[str, float, float, float, float, float, str]:
        """计算实虚值状态、内在价值、时间价值与保本点 (私有辅助方法)."""
        atm_threshold = 0.015  # 偏差在 1.5% 以内属于平价 ATM
        is_atm = (abs(spot - strike) / max(0.01, strike)) <= atm_threshold

        if opt_type == "call":
            intrinsic = max(0.0, spot - strike)
            if is_atm:
                moneyness = "平价 (ATM, At-the-Money)"
            elif spot > strike:
                moneyness = "实值 (ITM, In-the-Money)"
            else:
                moneyness = "虚值 (OTM, Out-of-the-Money)"

            time_val = max(0.0, premium - intrinsic)
            tv_ratio = time_val / premium if premium > 0 else 1.0
            break_even = strike + premium
            req_move_pct = ((break_even - safe_spot) / safe_spot) * 100.0

            if spot < strike:
                zero_warning = (
                    f"【极高归零风险】当前股价 ({curr_sym}{spot:.2f}) 处于行权价 "
                    f"({curr_sym}{strike:.2f}) 下方，属于虚值期权 (OTM)。内在价值为 {curr_sym}0，"
                    f"买入支付的权利金 ({curr_sym}{premium:.2f}) 100% 为时间价值。"
                    f"若到期时股价未能回升至 {curr_sym}{strike:.2f} 以上，该期权将毫无行权价值，"
                    f"本金 100% 全额亏损！"
                )
            else:
                zero_warning = (
                    f"当前处于实值/平价状态，含有每股 {curr_sym}{intrinsic:.2f} 内在价值保护垫。"
                    f"若到期股价跌破 {curr_sym}{strike:.2f}，仍将承受 100% 权利金损失。"
                )
        else:
            intrinsic = max(0.0, strike - spot)
            if is_atm:
                moneyness = "平价 (ATM, At-the-Money)"
            elif spot < strike:
                moneyness = "实值 (ITM, In-the-Money)"
            else:
                moneyness = "虚值 (OTM, Out-of-the-Money)"

            time_val = max(0.0, premium - intrinsic)
            tv_ratio = time_val / premium if premium > 0 else 1.0
            break_even = max(0.0, strike - premium)
            req_move_pct = ((break_even - safe_spot) / safe_spot) * 100.0

            if spot > strike:
                zero_warning = (
                    f"【极高归零风险】当前股价 ({curr_sym}{spot:.2f}) 处于行权价 "
                    f"({curr_sym}{strike:.2f}) 上方，属于虚值看跌期权 (OTM)。"
                    f"若到期时股价高于 {curr_sym}{strike:.2f}，期权价值归零，本金 100% 亏损！"
                )
            elif break_even <= 0.0:
                zero_warning = (
                    f"【极端无套利边界破损】买入权利金 ({curr_sym}{premium:.2f}) 超过行权价 "
                    f"({curr_sym}{strike:.2f})，标的即使归零亦无法保本，严禁买入！"
                )
            else:
                zero_warning = (
                    f"当前处于实值/平价看跌状态，含有每股 {curr_sym}{intrinsic:.2f} 内在价值。"
                    f"若到期股价高于 {curr_sym}{strike:.2f}，仍将承受 100% 权利金损失。"
                )

        return (
            moneyness,
            intrinsic,
            time_val,
            tv_ratio,
            break_even,
            req_move_pct,
            zero_warning,
        )

    @staticmethod
    def _calc_payoff(
        target_price: float, strike: float, premium: float, opt_type: str
    ) -> Tuple[float, float]:
        """计算特定情景下的单股净收益与收益率百分比 (私有静态方法)."""
        if opt_type == "call":
            exercise_val = max(0.0, target_price - strike)
        else:
            exercise_val = max(0.0, strike - target_price)
        net_profit = exercise_val - premium
        ret_pct = (net_profit / premium) * 100.0 if premium > 0 else 0.0
        return round(net_profit, 3), round(ret_pct, 2)

    @staticmethod
    def _compute_expectation_and_odds(
        scenarios: UnderlyingScenarios,
        bear_net: float,
        base_net: float,
        bull_net: float,
        premium: float,
    ) -> Tuple[float, float, float, float]:
        """计算数学期望收益、胜率与盈亏赔率 (私有静态方法)."""
        exp_profit = (
            scenarios.bear_prob * bear_net
            + scenarios.base_prob * base_net
            + scenarios.bull_prob * bull_net
        )
        exp_return_pct = (exp_profit / premium) * 100.0 if premium > 0 else 0.0

        win_prob = 0.0
        weighted_win_profit = 0.0
        weighted_loss_amount = 0.0
        for prob, profit in [
            (scenarios.bear_prob, bear_net),
            (scenarios.base_prob, base_net),
            (scenarios.bull_prob, bull_net),
        ]:
            if profit > 0:
                win_prob += prob
                weighted_win_profit += prob * profit
            else:
                weighted_loss_amount += prob * abs(profit)

        avg_win = (weighted_win_profit / win_prob) if win_prob > 0 else 0.0
        avg_loss = (weighted_loss_amount / (1.0 - win_prob)) if win_prob < 1.0 else premium
        safe_avg_loss = max(0.001, avg_loss)
        odds_b = (avg_win / safe_avg_loss) if safe_avg_loss > 0 else 1.0

        return exp_profit, exp_return_pct, win_prob, odds_b

    @classmethod
    def _determine_verdict_and_kelly(
        cls,
        contract: OptionContractInput,
        scenarios: UnderlyingScenarios,
        opt_type: str,
        spot: float,
        strike: float,
        premium: float,
        intrinsic: float,
        time_val: float,
        tv_ratio: float,
        break_even: float,
        req_move_pct: float,
        moneyness: str,
        bull_ret: float,
        exp_profit: float,
        exp_return_pct: float,
        win_prob: float,
        odds_b: float,
        curr_sym: str,
        freshness_label: str,
    ) -> Tuple[float, str, str, str, str]:
        """计算凯利仓位并生成去工程符号化的自然语言研报卡片 (私有辅助方法)."""
        opt_label = "看涨期权 (Call)" if opt_type == "call" else "看跌期权 (Put)"

        if opt_type == "call":
            if req_move_pct > 0:
                move_desc = f"上涨至少 {req_move_pct:.1f}%"
                break_even_condition_zh = f"需{move_desc}方能保本"
            else:
                move_desc = f"回调不超过 {abs(req_move_pct):.1f}%"
                break_even_condition_zh = f"已处于安全垫区间 (允许{move_desc}仍可保本)"
        else:
            if break_even <= 0.0:
                break_even_condition_zh = "权利金高过行权价，无法保本"
            elif req_move_pct < 0:
                move_desc = f"进一步下跌至少 {abs(req_move_pct):.1f}%"
                break_even_condition_zh = f"需{move_desc}方能保本"
            else:
                move_desc = f"反弹不超过 {req_move_pct:.1f}%"
                break_even_condition_zh = f"已处于安全垫区间 (允许{move_desc}仍可保本)"

        if exp_profit <= 0 or win_prob < 0.20 or odds_b < 0.5:
            rec_kelly_pct = 0.0
            verdict_zh = "严禁买入 (负期望彩票型期权)"
            verdict = verdict_zh
            if bull_ret > 0:
                upside_clause = (
                    f"虽然乐观情景下具备一定爆发弹性 ({bull_ret:+.1f}%)，但由于处于 {moneyness}"
                )
            else:
                upside_clause = (
                    f"即使在乐观情景下仍无法越过保本门槛导致本金折损 ({bull_ret:+.1f}%)，"
                    f"且处于 {moneyness}"
                )
            rationale = (
                f"经严密因果链推算，{upside_clause}，"
                f"标的{break_even_condition_zh}，数学期望净收益为负 ({exp_return_pct:+.1f}%)，"
                f"实际胜率仅为 {win_prob*100:.1f}%，归零踩踏概率极高，不符合理性买方投资纪律。"
            )
        else:
            loss_prob = 1.0 - win_prob
            full_kelly = max(0.0, (odds_b * win_prob - loss_prob) / odds_b) if odds_b > 0 else 0.0
            rec_kelly_pct = min(2.0, round(full_kelly * 0.25 * 100, 2))

            if moneyness.startswith("虚值"):
                verdict_zh = (
                    f"轻仓彩票型博弈 ({'看涨' if opt_type == 'call' else '看跌'}极低仓位配置)"
                )
                verdict = verdict_zh
                rationale = (
                    f"当前处于虚值{opt_label}，买入面临 100% 归零的高下行风险。但由于基准/乐观情景下"
                    f"赔率高达 {odds_b:.2f}，整体数学期望收益为 {exp_return_pct:+.1f}%。"
                    f"严格执行买方期权风控：权利金总投入严禁超过总资金的 {rec_kelly_pct:.2f}%，"
                    f"一旦跌破止损线或临近到期无催化剂，必须坚决果断止损。"
                )
            else:
                verdict_zh = (
                    f"高赔率非对称买入 ({'看涨' if opt_type == 'call' else '看跌'}非对称击球)"
                )
                verdict = verdict_zh
                rationale = (
                    f"标的处于实值/平价区间，享有每股 {curr_sym}{intrinsic:.2f} 内在价值保护。"
                    f"保本所需变动幅度适中 ({break_even_condition_zh})，胜率达 "
                    f"{win_prob*100:.1f}%，数学期望收益显著为正 ({exp_return_pct:+.1f}%)，"
                    f"建议以 1/4 凯利原则配置 {rec_kelly_pct:.2f}% 仓位。"
                )

        narrative_zh = (
            f"【标的 {contract.underlying_ticker} 期权因果全息研报】"
            f"标的现价 {curr_sym}{spot:.2f} ({freshness_label})，合约类型【{opt_label}】，"
            f"行权价 {curr_sym}{strike:.2f} (到期天数 {contract.days_to_expiration}天，"
            f"买入权利金 {curr_sym}{premium:.2f})。"
            f"中项性质拆解: 处于【{moneyness}】，每股内在价值 {curr_sym}{intrinsic:.2f}，"
            f"纯时间价值 {curr_sym}{time_val:.2f} (占比 {tv_ratio * 100:.1f}%)；"
            f"保本平衡点为 {curr_sym}{break_even:.2f} (标的{break_even_condition_zh})。"
            f"情景收益期望: 综合胜率 {win_prob * 100:.1f}%，盈亏赔率 {odds_b:.2f}，"
            f"数学期望净收益率 {exp_return_pct:+.1f}%。"
            f"买方风控与决策判定: 【{verdict_zh}】(1/4 凯利权利金配置上限 {rec_kelly_pct:.2f}%)。"
            f"{rationale}"
        )

        return rec_kelly_pct, verdict, verdict_zh, rationale, narrative_zh
