from pathlib import Path

from backtest_dsl import parse


def test_parse_example():
    source = Path("examples/vanilla_roll.bt").read_text()
    strategy = parse(source)
    assert strategy.name == "vanilla_roll"
    assert str(strategy.start_date) == "2025-01-02"
    assert str(strategy.end_date) == "2025-06-30"
    assert strategy.initial_notional.amount == 1_000_000
    assert strategy.roll_every == "3W"
    assert strategy.option.tenor == "1M"
