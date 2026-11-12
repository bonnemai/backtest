import asyncio
from datetime import date

import pytest

from backtest_dsl import BacktestEngine, BacktestInput, QuantLibInput, parse


class FlatInput(BacktestInput):
    async def get_vanilla(
        self, *, as_of_date, expiry, strike, option_kind="call"
    ):
        return {
            "premium": 0.025,
            "forward": 1.0,
            "vol": 0.20,
            "delta": 0.50,
            "gamma": 1.0,
            "vega": 0.10,
            "theta": -0.01,
        }

    async def get_atmf_strike(self, *, as_of_date, expiry):
        return 1.0


def test_engine_accepts_abstract_input():
    strategy = parse(
        '''strategy "smoke" {
        initial_cash 50000 USD;
        start 2025-01-02;
        end 2025-01-03;
        buy notional 1M USD vanilla(underlying "EURUSD", kind call,
          strike atmf, tenor 1M);
        every 3W { sell position; buy with cash vanilla(
          underlying "EURUSD", kind call, strike atmf, tenor 1M); }
        }'''
    )

    snapshots = asyncio.run(
        BacktestEngine(FlatInput()).run(
            strategy, dates=[date(2025, 1, 2), date(2025, 1, 3)]
        )
    )

    assert len(snapshots) == 2
    assert snapshots[0].option_value == pytest.approx(25_000)


def test_quantlib_input_uses_twenty_percent_volatility():
    pytest.importorskip("QuantLib")
    market = QuantLibInput(volatility=0.20)

    quote = asyncio.run(
        market.get_vanilla(
            as_of_date=date(2025, 1, 2),
            expiry=date(2025, 2, 3),
            strike=1.0,
            option_kind="put",
        )
    )

    assert quote["vol"] == pytest.approx(0.20)
    assert quote["premium"] > 0
    assert quote["forward"] == pytest.approx(1.0)
