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
