# Harbor Market contribution rules

- Python 3.14, uv, Django, standard ORM and migrations. No dependency major caps.
- M1 establishes vocabulary, package boundaries and verification only.
- Domain uses the standard library; application coordinates domain objects and ports.
- Infrastructure implements ports; presentation translates requests and templates.
- Only composition wires concrete adapters. Keep framework imports out of the core.
- Run `make check`; keep results, databases and credentials untracked.
- One issue and one small pull request per purpose. No generated author signatures.
- CI runs only lint, typing, import contracts and unit tests on pull requests.
- No containers, external artwork, external model services or deployment.
- Keep `docs/theory` in step with the code: a new rule gets a page section, a figure and a table
  row in the same pull request; `make theory-figs` and `make theory-check` must pass, and the
  README's statement count (8) must match the table.
- Style: `make fmt` rewrites, `make check-style` = `make lint` (Ruff format check + every Ruff rule) and
  `make typecheck` (mypy strict). No ignore files, excludes or inline suppressions; fix the code. The only
  rules left out are the pairs Ruff marks incompatible (D203/D213, COM812) and S101 in tests (pytest asserts).
