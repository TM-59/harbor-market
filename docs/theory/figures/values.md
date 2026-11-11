# Measured values

Written by `make theory-figs` (scripts/theory_figs.py) from the domain itself. Do not edit by hand.
The last column is the relative error; where the theory column is 0 it is the absolute value.

| id | what is measured | measured | theory | error |
|---|---|---|---|---|
| `coins-rejected` | coin amounts refused: negative, fractional, text, a truth value (theory 4) | 4 | 4 | 0.00e+00 |
| `cargo-rejected` | cargos refused: nine of one good, nine in total, negative, fractional (theory 4) | 4 | 4 | 0.00e+00 |
| `cargo-capacity` | slots in the hold | 8 | 8 | 0.00e+00 |
| `quote-rejected` | prices refused: zero, negative, fractional (theory 3) | 3 | 3 | 0.00e+00 |
| `market-days` | market days | 6 | 6 | 0.00e+00 |
| `market-low` | lowest price in the table | 2 | 2 | 0.00e+00 |
| `market-high` | highest price in the table | 7 | 7 | 0.00e+00 |
| `market-valuation` | 3 grain and 2 salt valued at day-1 prices, coins (theory 3·3 + 2·5) | 19 | 19 | 0.00e+00 |
| `market-same-table` | two new sessions see the same six days of quotes (1 = yes) | 1 | 1 | 0.00e+00 |
| `trade-buy-coins` | coins after buying 4 grain at 3 from 20 (theory 20 − 12) | 8 | 8 | 0.00e+00 |
| `trade-buy-cargo` | grain held after that purchase | 4 | 4 | 0.00e+00 |
| `trade-event` | the TradeExecuted event carries the resulting coins and cargo (1 = yes) | 1 | 1 | 0.00e+00 |
| `trade-sell-coins` | coins after selling 2 grain at 4 on day 2 (theory 8 + 8) | 16 | 16 | 0.00e+00 |
| `trade-refused` | invalid trades refused: zero quantity, too dear, too many, two short sales (theory 5) | 5 | 5 | 0.00e+00 |
| `trade-refused-unchanged` | day, coins and cargo unchanged after those refusals (1 = yes) | 1 | 1 | 0.00e+00 |
| `feasible-accepted` | day 3 with 38 coins: purchases (grain, salt), 0 to 9 of each, that are accepted, of 100 (theory: 2g + 6s ≤ 38 and g + s ≤ 8) | 41 | 41 | 0.00e+00 |
| `feasible-refused` | of those 100, refused for coins or for cargo space | 59 | 59 | 0.00e+00 |
| `feasible-coins` | of the refused, the session names coins (reported, no theory) | 39 | 39 | 0.00e+00 |
| `feasible-space` | of the refused, the session names cargo space (reported, no theory) | 20 | 20 | 0.00e+00 |
| `worth-trade-drift` | sum of |change of worth| over the 9 trades of the best plan, coins | 0 | 0 | 0.00e+00 |
| `worth-events` | events emitted by the best plan: 9 trades, 5 days advanced, 1 settlement | 15 | 15 | 0.00e+00 |
| `worth-final` | settled coins of the best plan | 118 | 118 | 0.00e+00 |
| `worth-night-gain` | sum of the six overnight changes of worth in the best plan, coins (theory 118 − 20) | 98 | 98 | 0.00e+00 |
| `days-sequence` | days visited by a session that only advances (theory 6) | 6 | 6 | 0.00e+00 |
| `idle-settles` | settled coins of a session that never trades | 20 | 20 | 0.00e+00 |
| `settled-refuses` | actions refused by a settled session: buy, sell, advance (theory 3) | 3 | 3 | 0.00e+00 |
| `settle-liquidation` | day 6, 4 coins, 2 grain, 3 salt: settled coins (theory 4 + 2·6 + 3·5) | 31 | 31 | 0.00e+00 |
| `settle-empties` | units left in the hold after settlement | 0 | 0 | 0.00e+00 |
| `search-states` | states (day, coins, grain, salt) reachable through the aggregate | 10011 | 10011 | 0.00e+00 |
| `search-best` | largest settled coins over every reachable play | 118 | 118 | 0.00e+00 |
| `search-worst` | smallest settled coins over every reachable play | 3 | 3 | 0.00e+00 |
| `search-distinct` | distinct settled amounts | 116 | 116 | 0.00e+00 |
| `greedy-final` | worth on day 6 when each night carries the largest affordable gain | 118 | 118 | 0.00e+00 |
| `greedy-matches-search` | the nightly rule reaches the searched optimum (1 = yes) | 1 | 1 | 0.00e+00 |
| `replay-identical` | the same actions give the same session twice (1 = yes) | 1 | 1 | 0.00e+00 |
