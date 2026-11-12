from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from .ast import Strategy
from .inputs import BacktestInput


@dataclass(frozen=True)
class Snapshot:
    as_of_date: date
    cash: float
    notional: float
    option_value: float
    nav: float
    pnl: float = 0.0
    delta_pnl: float = 0.0
    gamma_pnl: float = 0.0
    vega_pnl: float = 0.0
    theta_pnl: float = 0.0
    residual_pnl: float = 0.0
    underlying_change: float = 0.0
    volatility_change: float = 0.0


class BacktestEngine:
    def __init__(self, input: BacktestInput):
        self.input = input

    async def run(
        self,
        strategy: Strategy,
        dates: Iterable[date] | None = None,
    ) -> list[Snapshot]:
        dates = list(dates) if dates is not None else list(
            _business_days(strategy.start_date, strategy.end_date)
        )
        if not dates:
            return []

        cash = strategy.initial_cash.amount
        notional = 0.0
        strike = 0.0
        expiry = dates[0]
        next_roll = dates[0]
        output: list[Snapshot] = []
        previous_date: date | None = None
        previous_quote: dict | None = None
        previous_nav: float | None = None
        previous_notional = 0.0

        for today in dates:
            rolled = today >= next_roll
            if rolled:
                if notional:
                    old = await self._quote(today, expiry, strike, strategy)
                    cash += notional * old["premium"]

                expiry = today + _duration(strategy.option.tenor)
                strike = await self.input.get_atmf_strike(
                    as_of_date=today, expiry=expiry
                )
                fresh = await self._quote(today, expiry, strike, strategy)

                if notional == 0.0:
                    notional = strategy.initial_notional.amount
                else:
                    notional = cash / fresh["premium"] if fresh["premium"] else 0.0

                cash -= notional * fresh["premium"]
                next_roll = today + _duration(strategy.roll_every)

            marked = await self._quote(today, expiry, strike, strategy)
            option_value = notional * marked["premium"]
            nav = cash + option_value

            # Greeks explain the change in value of the same position. At a
            # roll, the old contract and the new one are different, so we
            # reset the attribution and leave any difference as residual P&L.
            if previous_nav is None:
                daily_pnl = 0.0
                delta_pnl = gamma_pnl = vega_pnl = theta_pnl = 0.0
                underlying_change = volatility_change = 0.0
            elif rolled or previous_quote is None:
                daily_pnl = nav - previous_nav
                delta_pnl = gamma_pnl = vega_pnl = theta_pnl = 0.0
                underlying_change = volatility_change = 0.0
            else:
                daily_pnl = nav - previous_nav
                underlying_change = _change(marked, previous_quote, "forward", "spot")
                volatility_change = _change(marked, previous_quote, "vol")
                assert previous_date is not None
                year_fraction = (today - previous_date).days / 365.0

                delta = previous_quote.get("delta", 0.0)
                gamma = previous_quote.get("gamma", 0.0)
                vega = previous_quote.get("vega", 0.0)
                theta = previous_quote.get("theta", 0.0)
                delta_pnl = previous_notional * delta * underlying_change
                gamma_pnl = (
                    0.5 * previous_notional * gamma * underlying_change**2
                )
                vega_pnl = previous_notional * vega * volatility_change
                theta_pnl = previous_notional * theta * year_fraction

            explained = delta_pnl + gamma_pnl + vega_pnl + theta_pnl
            residual_pnl = daily_pnl - explained
            output.append(
                Snapshot(
                    today,
                    cash,
                    notional,
                    option_value,
                    nav,
                    daily_pnl,
                    delta_pnl,
                    gamma_pnl,
                    vega_pnl,
                    theta_pnl,
                    residual_pnl,
                    underlying_change,
                    volatility_change,
                )
            )

            previous_date = today
            previous_quote = marked
            previous_nav = nav
            previous_notional = notional

        return output

    async def _quote(self, today, expiry, strike, strategy):
        return await self.input.get_vanilla(
            as_of_date=today,
            expiry=expiry,
            strike=strike,
            option_kind=strategy.option.kind,
        )


def _change(current: dict, previous: dict, *keys: str) -> float:
    """Return the first available market-factor change, or zero if absent."""
    for key in keys:
        if key in current and key in previous:
            return current[key] - previous[key]
    return 0.0


def _duration(value: str) -> timedelta:
    number, unit = int(value[:-1]), value[-1]
    if unit == "D":
        return timedelta(days=number)
    if unit == "W":
        return timedelta(weeks=number)
    if unit == "M":
        return timedelta(days=30 * number)
    if unit == "Y":
        return timedelta(days=365 * number)
    raise ValueError(f"Durée inconnue : {value}")


def _business_days(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)
