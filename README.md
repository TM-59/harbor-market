# Harbor Market

A single-player harbor trading game designed around coins, limited cargo and six
market days. M2 implements the trading rules as a pure domain: 20 starting coins,
a hold of eight units, grain and salt at fixed daily quotes, and settlement after
day six. Persistence and browser gameplay are not yet implemented. There is no
playable screenshot to show at this stage.

The rules can be tried from Python without Django:

```sh
PYTHONPATH=src python3 -c "
from harbor_market.domain import Good, TradingSession
session = TradingSession('demo')
print(session.buy(Good.GRAIN, 6))
print(session.advance())
print(session.sell(Good.GRAIN, 6))
"
```

Doing nothing settles at 20 coins; the best plan reaches 118.

**Theory handbook**: [docs/theory/](docs/theory/README.md) — 8 statements (the language, whole and bounded
values, the market table, one trade, conservation of worth, settlement, why 118 is the most, the dependency
rule), each with its rule, assumptions, derivation, code, tests and a figure. `make theory-figs` regenerates
the figures and the measured values; `make theory-check` checks the coverage table.

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```sh
make sync
make check
make serve
```

Open `http://localhost:8000/health/` for `{"status":"ok"}`. The development
entry generates an ephemeral signing key in memory; no credential is stored.
This scaffold is for local use and is not deployment configuration.

`make test` runs pytest. `make check` adds Ruff, mypy, Import Linter and Django
system checks. Both save native JUnit and `test-results/summary.json` outside Git.
There is no simulation benchmark or browser smoke target before gameplay exists.
CI runs only the PR's lightweight checks; no push or scheduled test execution.

See [domain vocabulary and roadmap](docs/domain.md), [requirements](docs/requirements.md)
and [test inventory](test-inventory.json). M2 implements the pure domain, M3 adds
use cases and Django ORM/SQLite migrations, M4 adds the browser screen.
