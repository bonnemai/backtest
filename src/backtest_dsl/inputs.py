"""Market-data and pricing inputs used by the backtest engine."""

from abc import ABC, abstractmethod
from datetime import date
from math import exp
from typing import Any


class BacktestInput(ABC):
    """Abstract pricing input required by :class:`BacktestEngine`."""

    @abstractmethod
    async def get_vanilla(
        self,
        *,
        as_of_date: date,
        expiry: date,
        strike: float,
        option_kind: str = "call",
    ) -> dict[str, float]:
        """Return the option premium and the market data used to explain P&L."""

    @abstractmethod
    async def get_atmf_strike(self, *, as_of_date: date, expiry: date) -> float:
        """Return the at-the-money-forward strike for the requested maturity."""


class QuantLibInput(BacktestInput):
    """Minimal QuantLib Black-Scholes input for an initial smoke test.

    The market is intentionally flat: spot, rates and dividend yield are
    constant, and the volatility is constant by default at 20%. QuantLib is
    imported lazily so the base package remains usable without the optional
    dependency.
    """

    def __init__(
        self,
        *,
        spot: float = 1.0,
        volatility: float = 0.20,
        risk_free_rate: float = 0.0,
        dividend_yield: float = 0.0,
    ) -> None:
        if spot <= 0:
            raise ValueError("spot doit être strictement positif")
        if volatility < 0:
            raise ValueError("volatility ne peut pas être négative")
        self.spot = spot
        self.volatility = volatility
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield

    async def get_atmf_strike(self, *, as_of_date: date, expiry: date) -> float:
        year_fraction = _year_fraction(as_of_date, expiry)
        return self.spot * exp((self.risk_free_rate - self.dividend_yield) * year_fraction)

    async def get_vanilla(
        self,
        *,
        as_of_date: date,
        expiry: date,
        strike: float,
        option_kind: str = "call",
    ) -> dict[str, float]:
        if option_kind not in {"call", "put"}:
            raise ValueError("option_kind doit être 'call' ou 'put'")
        ql = _quantlib()
        evaluation_date = _ql_date(ql, as_of_date)
        maturity_date = _ql_date(ql, expiry)
        day_count = ql.Actual365Fixed()
        calendar = ql.NullCalendar()

        ql.Settings.instance().evaluationDate = evaluation_date
        spot = ql.QuoteHandle(ql.SimpleQuote(self.spot))
        rates = ql.YieldTermStructureHandle(
            ql.FlatForward(evaluation_date, self.risk_free_rate, day_count)
        )
        dividends = ql.YieldTermStructureHandle(
            ql.FlatForward(evaluation_date, self.dividend_yield, day_count)
        )
        volatility = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(evaluation_date, calendar, self.volatility, day_count)
        )
        process = ql.BlackScholesMertonProcess(spot, dividends, rates, volatility)
        payoff_kind = ql.Option.Call if option_kind == "call" else ql.Option.Put
        option = ql.VanillaOption(
            ql.PlainVanillaPayoff(payoff_kind, strike),
            ql.EuropeanExercise(maturity_date),
        )
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))

        # Normalize the price and vega to the spot unit so they match the
        # engine's convention: premium is a fraction of notional and vega is
        # per unit of absolute volatility.
        return {
            "premium": option.NPV() / self.spot,
            "forward": await self.get_atmf_strike(
                as_of_date=as_of_date, expiry=expiry
            ),
            "vol": self.volatility,
            "delta": option.delta(),
            "gamma": option.gamma() * self.spot,
            "vega": option.vega() / self.spot,
            "theta": option.theta() / self.spot,
        }


def _quantlib() -> Any:
    try:
        import QuantLib as ql
    except ImportError as exc:  # pragma: no cover - exercised without optional dep
        raise ImportError(
            "QuantLib est optionnel : installez 'backtest-dsl[quantlib]'"
        ) from exc
    return ql


def _ql_date(ql: Any, value: date) -> Any:
    return ql.Date(value.day, value.month, value.year)


def _year_fraction(start: date, end: date) -> float:
    return (end - start).days / 365.0
