# Requirements

- REQ-HEALTH: GET /health/ returns status ok as JSON; other methods are rejected.
- REQ-CORE: domain/application import without frameworks; adapters point inward.
- REQ-CHECK: local make checks save native JUnit and a summary, including failures.
- REQ-USECASE: start, buy, sell, advance and read are application use cases behind
  a repository port; unknown sessions and invalid domain actions fail explicitly.
- REQ-PERSISTENCE: SQLite restores session identity, day, coins, cargo, settlement
  state, revision and ordered domain-event history after connections close/reopen.
- REQ-REVISION: revision starts at zero and increments once per saved action; a
  stale snapshot cannot overwrite a committed action and raises `SessionConflict`.
- REQ-ATOMIC: session state and events commit together; an event write failure rolls
  back the session update.

Test names carry requirement IDs. Import Linter also enforces REQ-CORE.
REQ-CHECK is verified with isolated failure/timeout runs during scaffold acceptance.
The ORM integration suite uses Django's isolated test database and migrations.

M2, the pure domain (standard library only; see tests/test_domain.py):

- REQ-VALUE: coins, cargo and quotes are immutable whole-number values; cargo holds at most eight units; the six-day table is fixed.
- REQ-TRADE: buying and selling use the day's quote and give exact balances; quantities are positive whole numbers; no overspending, overloading or short selling; an invalid trade changes nothing.
- REQ-DAY: five advances reach day six; advancing from day six sells the cargo at day-six quotes and settles; settled sessions reject every action; the best plan reaches the computed optimum.

`make test` runs unit tests; `make check` also runs ORM integration tests. CI runs
lint, format, typing, import contracts, Django system checks and both test suites.
Native JUnit is written separately for unit and integration; `test-results/` and
SQLite files remain untracked.
