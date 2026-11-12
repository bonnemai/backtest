# Backtest DSL — première version

Cette première version décrit une stratégie de roll d'options dans un petit
langage déclaratif. L'exemple [`examples/vanilla_roll.bt`](examples/vanilla_roll.bt)
exprime :

```text
acheter 1M USD de notionnel ATMF, maturité 1M
tous les 3W : vendre, puis réinvestir tout le cash dans une nouvelle option
```

Le projet utilise **ANTLR4** pour définir et générer le parseur de la DSL, et
**QuantLib** pour le pricing des options et le calcul des sensibilités dans
l'adaptateur de marché de test. Ces deux composants sont optionnels selon le
besoin : ANTLR est installé avec `.[antlr]` et QuantLib avec `.[quantlib]`.

La grammaire de référence est [`grammar/Backtest.g4`](grammar/Backtest.g4).
Elle est compatible avec ANTLR4. Le module [`parser.py`](src/backtest_dsl/parser.py)
contient pour l'instant un parseur Python sans dépendance, afin que l'AST et le
moteur soient utilisables avant la génération des fichiers ANTLR.

## Générer le parseur ANTLR

Il n'est pas nécessaire de télécharger manuellement le JAR. ANTLR fournit
`antlr4-tools`, installable depuis Python. Cet outil crée la commande `antlr4`
et télécharge le JAR au premier lancement ; il peut également installer un JRE
si Java n'est pas présent. Le runtime Python reste séparé : il sert à exécuter
les classes générées.

Installation :

```bash
python -m pip install -e '.[antlr]'
```

Génération :

```bash
ANTLR4_TOOLS_ANTLR_VERSION=4.13.2 antlr4 \
  -Dlanguage=Python3 \
  -visitor \
  -o src/backtest_dsl/generated \
  grammar/Backtest.g4
```

Le verrouillage de la version est volontaire : il évite que `antlr4-tools`
essaie d'interroger automatiquement Sonatype pour trouver la dernière version.
Cette détection peut échouer avec une réponse HTTP 400. La même variable peut
être exportée pour la session :

```bash
export ANTLR4_TOOLS_ANTLR_VERSION=4.13.2
antlr4 -Dlanguage=Python3 -visitor \
  -o src/backtest_dsl/generated grammar/Backtest.g4
```

Le JAR et les fichiers téléchargés sont des dépendances/outils locaux ; ils ne
doivent pas être commités. Les versions du générateur et de
`antlr4-python3-runtime` doivent rester identiques, conformément à la
documentation du target Python ANTLR.

L'étape suivante consistera à remplacer l'adaptateur de parsing par un
`BacktestVisitor` généré, sans modifier le moteur de backtest.

## Contrat de pricing

Le moteur reçoit une implémentation de `BacktestInput`, qui regroupe le prix
de l'option et le calcul du strike ATMF :

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

`premium` est supposée être une fraction du notionnel. Une prime de `0.025`
sur un notionnel de `1_000_000` vaut donc `25_000` USD.

Le résultat du moteur contient également `pnl`, `delta_pnl`, `gamma_pnl`,
`vega_pnl`, `theta_pnl` et `residual_pnl`. L'approximation utilisée entre deux
dates est :

```text
delta P&L = N × delta × Δforward
gamma P&L = 0.5 × N × gamma × Δforward²
vega P&L  = N × vega × Δvol
theta P&L = N × theta × Δt
résiduel  = P&L observé - somme des contributions
```

`theta` est supposé exprimé par année et `vega` par unité de volatilité
absolue. Si `forward` n'est pas fourni, le moteur essaie d'utiliser `spot`.

## Période du backtest

Les dates font partie des inputs de la stratégie :

```text
initial_cash 50000 USD;
start 2025-01-02;
end 2025-06-30;
```

Le moteur peut alors générer automatiquement les jours du lundi au vendredi :

```python
snapshots = await engine.run(strategy)
```

Pour gérer précisément les jours fériés, un calendrier externe peut toujours
être fourni :

```python
snapshots = await engine.run(strategy, dates=market_calendar)
```

### Premier test avec QuantLib

QuantLib est disponible comme dépendance optionnelle. `QuantLibInput` utilise
un modèle Black-Scholes avec spot 1.0, taux nuls et volatilité constante de
20 % par défaut :

```bash
python -m pip install -e '.[quantlib]'
```

```python
from backtest_dsl import BacktestEngine, QuantLibInput

engine = BacktestEngine(QuantLibInput(volatility=0.20))
snapshots = await engine.run(strategy)
```
