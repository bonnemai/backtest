"""Small dependency-free parser matching grammar/Backtest.g4.

The parser is intentionally kept as a fallback while generated ANTLR files are
not committed. It can later be replaced by BacktestLexer/BacktestParser without
changing the AST or engine.
"""

import re
from datetime import date

from .ast import Money, Strategy, VanillaSpec


_PATTERN = re.compile(
    r"strategy\s+\"(?P<name>[^\"]+)\"\s*\{"
    r"\s*(?:initial_cash\s+(?P<cash>[0-9.]+)\s+(?P<cash_ccy>[A-Z]{3})\s*;)?"
    r"\s*start\s+(?P<start>[0-9]{4}-[0-9]{2}-[0-9]{2})\s*;"
    r"\s*end\s+(?P<end>[0-9]{4}-[0-9]{2}-[0-9]{2})\s*;"
    r"\s*buy\s+notional\s+(?P<notional>[0-9.]+)(?P<notional_scale>[KMB])?\s+"
    r"(?P<notional_ccy>[A-Z]{3})\s+"
    r"vanilla\(\s*underlying\s+\"(?P<underlying>[^\"]+)\"\s*,"
    r"\s*kind\s+(?P<kind>call|put)\s*,\s*strike\s+atmf\s*,"
    r"\s*tenor\s+(?P<tenor>[0-9]+[DWMY])\s*\)\s*;"
    r"\s*every\s+(?P<roll>[0-9]+[DWMY])\s*\{\s*sell\s+position\s*;"
    r"\s*buy\s+with\s+cash\s+vanilla\(\s*underlying\s+\"(?P<r_underlying>[^\"]+)\"\s*,"
    r"\s*kind\s+(?P<r_kind>call|put)\s*,\s*strike\s+atmf\s*,"
    r"\s*tenor\s+(?P<r_tenor>[0-9]+[DWMY])\s*\)\s*;\s*\}\s*\}\s*"
)


def parse(source: str) -> Strategy:
    match = _PATTERN.fullmatch(source)
    if not match:
        raise SyntaxError("Stratégie invalide : syntaxe attendue dans grammar/Backtest.g4")

    values = match.groupdict()
    option = VanillaSpec(
        underlying=values["underlying"],
        kind=values["kind"],
        strike="atmf",
        tenor=values["tenor"],
    )
    return Strategy(
        name=values["name"],
        initial_cash=Money(
            float(values["cash"] or 0), values["cash_ccy"] or "USD"
        ),
        start_date=date.fromisoformat(values["start"]),
        end_date=date.fromisoformat(values["end"]),
        initial_notional=Money(
            _notional_amount(values["notional"], values["notional_scale"]),
            values["notional_ccy"],
        ),
        option=option,
        roll_every=values["roll"],
    )


def _notional_amount(value: str, unit: str | None) -> float:
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    return float(value) * multipliers.get(unit or "", 1)
