# Requirements (M1 and M2)

- REQ-HEALTH: GET /health/ returns status ok as JSON; other methods are rejected.
- REQ-CORE: domain/application import without frameworks; adapters point inward.
- REQ-CHECK: local make checks save native JUnit and a summary, including failures.

Test names carry requirement IDs. Import Linter also enforces REQ-CORE.
REQ-CHECK is verified with isolated failure/timeout runs during scaffold acceptance.

M2, the pure domain (standard library only; see tests/test_domain.py):

- REQ-VALUE: coins, cargo and quotes are immutable whole-number values; cargo holds at most eight units; the six-day table is fixed.
- REQ-TRADE: buying and selling use the day's quote and give exact balances; quantities are positive whole numbers; no overspending, overloading or short selling; an invalid trade changes nothing.
- REQ-DAY: five advances reach day six; advancing from day six sells the cargo at day-six quotes and settles; settled sessions reject every action; the best plan reaches the computed optimum.
