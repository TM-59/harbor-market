# M1 requirements

- REQ-HEALTH: GET /health/ returns status ok as JSON; other methods are rejected.
- REQ-CORE: domain/application import without frameworks; adapters point inward.
- REQ-CHECK: local make checks save native JUnit and a summary, including failures.

Test names carry requirement IDs. Import Linter also enforces REQ-CORE.
REQ-CHECK is verified with isolated failure/timeout runs during scaffold acceptance.
Gameplay rules in domain.md are the M2 contract, not implemented M1 requirements.
