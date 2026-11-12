from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Money:
    amount: float
    currency: str


@dataclass(frozen=True)
class VanillaSpec:
    underlying: str
    kind: str
    strike: str
    tenor: str


@dataclass(frozen=True)
class Strategy:
    name: str
    initial_cash: Money
    start_date: date
    end_date: date
    initial_notional: Money
    option: VanillaSpec
    roll_every: str

