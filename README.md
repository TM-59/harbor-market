# Harbor Market

A single-player harbor trading game designed around coins, limited cargo and six
market days. The current M1 establishes vocabulary, dependency boundaries and a
Django health route. Trading rules, persistence and browser gameplay are not yet
implemented. There is no playable screenshot to show at this stage.

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
