# Backtest DSL — first version

This first version describes an option roll strategy in a small declarative
language. The example [`examples/vanilla_roll.bt`](examples/vanilla_roll.bt)
expresses:

```text
buy 1M USD of ATMF notional, with a 1M maturity
every 3W: sell, then reinvest all cash in a new option
```

The project uses **ANTLR4** to define and generate the DSL parser, and
**QuantLib** for option pricing and sensitivity calculations in the test market
adapter. Both components are optional: install ANTLR with `.[antlr]` and
QuantLib with `.[quantlib]`.

The reference grammar is [`grammar/Backtest.g4`](grammar/Backtest.g4), and is
compatible with ANTLR4. The [`parser.py`](src/backtest_dsl/parser.py) module
currently contains a dependency-free Python parser, so the AST and engine can
be used before generating the ANTLR files.

## Generate the ANTLR parser

There is no need to download the JAR manually. ANTLR provides `antlr4-tools`,
which can be installed from Python. This tool creates the `antlr4` command and
downloads the JAR on first use; it can also install a JRE if Java is not
available. The Python runtime remains separate and is used to run the generated
classes.

Install it with:

```bash
python -m pip install -e '.[antlr]'
```

Generate the parser with:

```bash
ANTLR4_TOOLS_ANTLR_VERSION=4.13.2 antlr4 \
  -Dlanguage=Python3 \
  -visitor \
  -o src/backtest_dsl/generated \
  grammar/Backtest.g4
```

The version is pinned intentionally: this prevents `antlr4-tools` from
automatically querying Sonatype for the latest version. That lookup can fail
with an HTTP 400 response. The same variable can be exported for the current
shell session:

```bash
export ANTLR4_TOOLS_ANTLR_VERSION=4.13.2
antlr4 -Dlanguage=Python3 -visitor \
  -o src/backtest_dsl/generated grammar/Backtest.g4
```

The JAR and downloaded files are local dependencies/tools and should not be
committed. The generator and `antlr4-python3-runtime` versions must remain
identical, as required by the ANTLR Python target documentation.

The next step is to replace the parsing adapter with a generated
`BacktestVisitor`, without modifying the backtest engine.

## Pricing contract

The engine receives a `BacktestInput` implementation that provides option
prices and ATMF strike calculations:

```python
from backtest_dsl import BacktestEngine, BacktestInput

class MyInput(BacktestInput):
    async def get_vanilla(
        self, *, as_of_date, expiry, strike, option_kind="call"
    ):
        return {
            "premium": 0.025,
            "forward": 1.085,
            "vol": 0.10,
            "delta": 0.50,
            "gamma": 1.20,
            "vega": 0.15,
            "theta": -0.08,
        }

    async def get_atmf_strike(self, *, as_of_date, expiry):
        return 1.085

engine = BacktestEngine(MyInput())
```

`premium` is assumed to be a fraction of notional. A premium of `0.025` on a
notional of `1_000_000` is therefore worth `25_000` USD.

The engine output also contains `pnl`, `delta_pnl`, `gamma_pnl`, `vega_pnl`,
`theta_pnl`, and `residual_pnl`. The approximation used between two dates is:

```text
delta P&L = N × delta × Δforward
gamma P&L = 0.5 × N × gamma × Δforward²
vega P&L  = N × vega × Δvol
theta P&L = N × theta × Δt
residual  = observed P&L - sum of contributions
```

`theta` is assumed to be expressed per year and `vega` per unit of absolute
volatility. If `forward` is not provided, the engine tries to use `spot`.

## Backtest period

Dates are part of the strategy inputs:

```text
initial_cash 50000 USD;
start 2025-01-02;
end 2025-06-30;
```

The engine can automatically generate weekdays from Monday to Friday:

```python
snapshots = await engine.run(strategy)
```

To handle holidays precisely, an external calendar can be provided:

```python
snapshots = await engine.run(strategy, dates=market_calendar)
```

### First QuantLib test

QuantLib is available as an optional dependency. `QuantLibInput` uses a
Black-Scholes model with spot 1.0, zero rates, and constant volatility of 20%
by default:

```bash
python -m pip install -e '.[quantlib]'
```

```python
from backtest_dsl import BacktestEngine, QuantLibInput

engine = BacktestEngine(QuantLibInput(volatility=0.20))
snapshots = await engine.run(strategy)
```

