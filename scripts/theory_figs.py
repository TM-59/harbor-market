"""Regenerates the drawn figures and the measured-values table of docs/theory.

Run with `make theory-figs`. Everything is computed by the domain itself
(src/harbor_market/domain); nothing here changes it. Standard library only.
"""

from __future__ import annotations

import sys
from collections import Counter, deque
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from harbor_market.domain import (  # noqa: E402
    CAPACITY,
    DAYS,
    MARKET,
    STARTING_COINS,
    Cargo,
    CargoValuation,
    Coins,
    DayAdvanced,
    Good,
    InvalidTrade,
    Quote,
    SessionClosed,
    SessionSettled,
    Side,
    TradeExecuted,
    TradingSession,
)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/theory/figures"
ROWS: list[str] = []
GRAIN, SALT = Good.GRAIN, Good.SALT
COLOUR = {GRAIN: "#c8961e", SALT: "#1f77b4"}
State = tuple[int, int, int, int]  # day, coins, grain, salt


def value(key: str, what: str, measured: float, theory: float) -> None:
    """One row of the table: id | what | measured | theory | error (absolute when theory is 0)."""
    error = abs(measured / theory - 1) if theory else abs(measured - theory)
    ROWS.append(f"| `{key}` | {what} | {measured:.8g} | {theory:.8g} | {error:.2e} |")


def svg(name: str, width: float, height: float, body: list[str]) -> None:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" font-family="sans-serif" font-size="12">'
    )
    text = "\n".join(
        [head, f'<rect width="{width:.0f}" height="{height:.0f}" fill="#ffffff"/>', *body, "</svg>"]
    )
    (OUT / name).write_text(text + "\n", encoding="utf-8")


def title(text: str) -> str:
    return f'<text x="16" y="26" font-size="16" font-weight="bold" fill="#222">{text}</text>'


def worth(session: TradingSession) -> int:
    return session.coins.amount + CargoValuation.value(session.cargo, session.quotes).amount


def price(day: int, good: Good) -> int:
    return MARKET[day - 1][good].price


def hold_figure() -> None:
    """Three cargos drawn as eight slots, and the ninth unit that is refused."""
    examples = [
        ("empty hold: 0 of 8", Cargo()),
        ("3 grain and 2 salt: 5 of 8", Cargo(3, 2)),
        ("8 grain: full; one more unit is refused", Cargo(8, 0)),
    ]
    body = [title("The hold: eight slots, one unit of either good per slot")]
    for i, (caption, cargo) in enumerate(examples):
        y = 60 + i * 74
        body.append(f'<text x="30" y="{y - 8}" fill="#222">{caption}</text>')
        filled = [GRAIN] * cargo.grain + [SALT] * cargo.salt
        for slot in range(CAPACITY):
            fill = COLOUR[filled[slot]] if slot < len(filled) else "#f4f4f4"
            body.append(
                f'<rect x="{30 + slot * 46}" y="{y}" width="40" height="40" fill="{fill}" stroke="#999"/>'
            )
            if slot < len(filled):
                letter = "g" if filled[slot] is GRAIN else "s"
                body.append(
                    f'<text x="{50 + slot * 46}" y="{y + 25}" text-anchor="middle" fill="#fff">{letter}</text>'
                )
    y = 60 + 2 * 74
    body.append(
        f'<rect x="{30 + CAPACITY * 46 + 14}" y="{y}" width="40" height="40" fill="none" stroke="#d62728" stroke-dasharray="5 4"/>'
    )
    body.append(
        f'<text x="{50 + CAPACITY * 46 + 14}" y="{y + 25}" text-anchor="middle" fill="#d62728">9th</text>'
    )
    svg("hold.svg", 520, 270, body)


def prices_figure() -> None:
    """The six-day price table as two lines, with the overnight changes written on them."""
    left, top, plot_w, plot_h, peak = 60, 50, 560, 220, 8
    body = [title("The market: price per unit of grain and salt on the six days")]
    body.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#888"/>'
    )

    def at(day: int, coins: float) -> tuple[float, float]:
        return left + (day - 0.5) * plot_w / DAYS, top + plot_h - coins / peak * plot_h

    for level in range(0, peak + 1, 2):
        _, y = at(1, level)
        body.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#444">{level}</text>'
        )
    for day in range(1, DAYS + 1):
        x, _ = at(day, 0)
        body.append(
            f'<text x="{x:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="#444">day {day}</text>'
        )
    for good in Good:
        points = [at(day, price(day, good)) for day in range(1, DAYS + 1)]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        body.append(
            f'<polyline points="{path}" fill="none" stroke="{COLOUR[good]}" stroke-width="3"/>'
        )
        for day, (x, y) in enumerate(points, start=1):
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{COLOUR[good]}"/>')
            shift = -10 if price(day, good) >= price(day, SALT if good is GRAIN else GRAIN) else 20
            body.append(
                f'<text x="{x:.1f}" y="{y + shift:.1f}" text-anchor="middle" fill="{COLOUR[good]}">{price(day, good)}</text>'
            )
    body.append(
        f'<text x="{left + 10}" y="{top + plot_h + 44}" fill="{COLOUR[GRAIN]}">grain</text>'
    )
    body.append(f'<text x="{left + 70}" y="{top + plot_h + 44}" fill="{COLOUR[SALT]}">salt</text>')
    body.append(
        f'<text x="{left + 130}" y="{top + plot_h + 44}" fill="#444">coins per unit; buying and selling use the same price</text>'
    )
    svg("prices.svg", 660, 330, body)


def feasible_figure() -> tuple[int, int, int]:
    """Every purchase (grain, salt) tried on day three with 38 coins: accepted or refused."""
    cell, left, top = 34, 70, 60
    body = [title("Day 3 with 38 coins: which purchases the session accepts")]
    accepted = short_of_coins = short_of_space = 0
    for grain in range(0, CAPACITY + 2):
        for salt in range(0, CAPACITY + 2):
            session = TradingSession("grid", 3, Coins(38))
            reason = ""
            try:
                if grain:
                    session.buy(GRAIN, grain)
                if salt:
                    session.buy(SALT, salt)
            except InvalidTrade as refusal:
                reason = str(refusal)
            if not reason:
                accepted += 1
                fill = "#2ca02c"
            elif "coins" in reason:
                short_of_coins += 1
                fill = "#d62728"
            else:
                short_of_space += 1
                fill = "#9467bd"
            x, y = left + grain * cell, top + (CAPACITY + 1 - salt) * cell
            body.append(
                f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" fill="{fill}" opacity="0.85"/>'
            )
            if not reason:
                body.append(
                    f'<text x="{x + 15}" y="{y + 20}" text-anchor="middle" fill="#fff" font-size="11">{session.coins.amount}</text>'
                )
    for n in range(0, CAPACITY + 2):
        body.append(
            f'<text x="{left + n * cell + 15}" y="{top + (CAPACITY + 2) * cell + 12}" text-anchor="middle" fill="#444">{n}</text>'
        )
        body.append(
            f'<text x="{left - 10}" y="{top + (CAPACITY + 1 - n) * cell + 20}" text-anchor="end" fill="#444">{n}</text>'
        )
    base = top + (CAPACITY + 2) * cell + 34
    body.append(f'<text x="{left}" y="{base}" fill="#444">grain bought (2 coins each) →</text>')
    body.append(f'<text x="16" y="{top - 8}" fill="#444">salt bought (6 coins each) ↑</text>')
    legend = [
        ("#2ca02c", "accepted; the number is the coins left"),
        ("#d62728", "refused: not enough coins"),
        ("#9467bd", "refused: not enough cargo space"),
    ]
    for i, (fill, text) in enumerate(legend):
        y = top + 20 + i * 24
        body.append(f'<rect x="440" y="{y - 12}" width="14" height="14" fill="{fill}"/>')
        body.append(f'<text x="462" y="{y}" fill="#222">{text}</text>')
    svg("feasible.svg", 720, base + 20, body)
    return accepted, short_of_coins, short_of_space


BEST_PLAN: list[tuple[Side | None, Good | None, int]] = [
    (Side.BUY, GRAIN, 6),
    (None, None, 0),
    (Side.SELL, GRAIN, 6),
    (Side.BUY, SALT, 6),
    (None, None, 0),
    (Side.SELL, SALT, 6),
    (Side.BUY, GRAIN, 8),
    (None, None, 0),
    (Side.SELL, GRAIN, 8),
    (Side.BUY, SALT, 8),
    (None, None, 0),
    (Side.SELL, SALT, 8),
    (Side.BUY, GRAIN, 8),
    (None, None, 0),
    (None, None, 0),
]


def play_best() -> tuple[list[tuple[str, int, int, bool]], int, int]:
    """Plays the best plan through the aggregate: (label, coins, worth, overnight) per step."""
    session = TradingSession("best")
    steps = [("start", session.coins.amount, worth(session), False)]
    trade_drift = events = 0
    for side, good, quantity in BEST_PLAN:
        before = worth(session)
        if side is None or good is None:
            event = session.advance()
            events += 1
            label = "settle" if isinstance(event, SessionSettled) else f"night → day {session.day}"
            after = session.coins.amount if session.settled else worth(session)
            steps.append((label, session.coins.amount, after, True))
            continue
        if side is Side.BUY:
            session.buy(good, quantity)
        else:
            session.sell(good, quantity)
        events += 1
        trade_drift += abs(worth(session) - before)
        steps.append(
            (f"{side.value} {quantity} {good.value}", session.coins.amount, worth(session), False)
        )
    return steps, trade_drift, events


def worth_figure(steps: list[tuple[str, int, int, bool]]) -> None:
    """Coins and worth after every step of the best plan: worth moves only overnight."""
    left, top, plot_w, plot_h, peak = 60, 50, 780, 240, 130
    step = plot_w / (len(steps) - 1)
    body = [title("The best plan step by step: coins, and worth = coins + cargo at today's prices")]
    body.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#888"/>'
    )

    def at(i: int, coins: float) -> tuple[float, float]:
        return left + i * step, top + plot_h - coins / peak * plot_h

    for level in range(0, peak + 1, 20):
        _, y = at(0, level)
        body.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#444">{level}</text>'
        )
    for i, (_, _, _, overnight) in enumerate(steps):
        if overnight:
            x0, _ = at(i - 1, 0)
            body.append(
                f'<rect x="{x0:.1f}" y="{top}" width="{step:.1f}" height="{plot_h}" fill="#eef3fa"/>'
            )
    series = ([row[1] for row in steps], "#999999"), ([row[2] for row in steps], "#d62728")
    for amounts, colour in series:
        points = [at(i, amount) for i, amount in enumerate(amounts)]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        body.append(f'<polyline points="{path}" fill="none" stroke="{colour}" stroke-width="3"/>')
    for i, (label, _, total, overnight) in enumerate(steps):
        x, y = at(i, total)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#d62728"/>')
        if overnight or i == 0:
            body.append(
                f'<text x="{x:.1f}" y="{y - 9:.1f}" text-anchor="middle" fill="#d62728">{total}</text>'
            )
        body.append(
            f'<text transform="translate({x + 4:.1f},{top + plot_h + 12}) rotate(55)" fill="#444" font-size="11">{label}</text>'
        )
    base = top + plot_h + 108
    body.append(f'<text x="{left}" y="{base}" fill="#d62728">worth</text>')
    body.append(f'<text x="{left + 50}" y="{base}" fill="#777">coins</text>')
    body.append(
        f'<text x="{left + 100}" y="{base}" fill="#444">shaded = a night passes (prices change); elsewhere a trade, which leaves worth flat</text>'
    )
    svg("worth.svg", 880, base + 16, body)


def reachable() -> tuple[int, Counter[int]]:
    """Every state reachable by one-unit trades and advancing, explored through the aggregate."""
    start: State = (1, STARTING_COINS, 0, 0)
    seen = {start}
    frontier = deque([start])
    settled: Counter[int] = Counter()
    while frontier:
        day, coins, grain, salt = frontier.popleft()
        for action in ("buy-grain", "buy-salt", "sell-grain", "sell-salt", "advance"):
            session = TradingSession("search", day, Coins(coins), Cargo(grain, salt))
            try:
                if action == "advance":
                    if isinstance(session.advance(), SessionSettled):
                        settled[session.coins.amount] += 1
                        continue
                else:
                    good = GRAIN if action.endswith("grain") else SALT
                    (session.buy if action.startswith("buy") else session.sell)(good, 1)
            except InvalidTrade:
                continue
            state: State = (
                session.day,
                session.coins.amount,
                session.cargo.grain,
                session.cargo.salt,
            )
            if state not in seen:
                seen.add(state)
                frontier.append(state)
    return len(seen), settled


def nightly_greedy() -> tuple[list[int], list[str]]:
    """Each night carry the cargo with the largest overnight gain that the worth can pay for."""
    wealth = STARTING_COINS
    history = [wealth]
    carried: list[str] = []
    for day in range(1, DAYS):
        top, choice = 0, (0, 0)
        for grain in range(CAPACITY + 1):
            for salt in range(CAPACITY + 1 - grain):
                if grain * price(day, GRAIN) + salt * price(day, SALT) > wealth:
                    continue
                gain = grain * (price(day + 1, GRAIN) - price(day, GRAIN)) + salt * (
                    price(day + 1, SALT) - price(day, SALT)
                )
                if gain > top:
                    top, choice = gain, (grain, salt)
        wealth += top
        history.append(wealth)
        carried.append(f"{choice[0]} grain" if choice[0] else f"{choice[1]} salt")
    return history, carried


def plan_figure(history: list[int], carried: list[str]) -> None:
    """Worth at the start of each day under the best plan, and what is carried overnight."""
    left, top, plot_w, plot_h, peak = 60, 50, 600, 230, 130
    step = plot_w / DAYS
    body = [title("The best plan: worth each morning, and the cargo carried into the next day")]
    for i, total in enumerate(history):
        bar = total / peak * plot_h
        x = left + i * step + step * 0.15
        body.append(
            f'<rect x="{x:.1f}" y="{top + plot_h - bar:.1f}" width="{step * 0.7:.1f}" height="{bar:.1f}" fill="#d62728" opacity="0.8"/>'
        )
        middle = left + i * step + step / 2
        body.append(
            f'<text x="{middle:.1f}" y="{top + plot_h - bar - 5:.1f}" text-anchor="middle" fill="#222">{total}</text>'
        )
        body.append(
            f'<text x="{middle:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="#444">day {i + 1}</text>'
        )
        if i < len(carried):
            edge = left + (i + 1) * step
            body.append(
                f'<text x="{edge:.1f}" y="{top + plot_h + 40}" text-anchor="middle" fill="#1f77b4">{carried[i]} →</text>'
            )
    body.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#888"/>'
    )
    svg("plan.svg", 700, top + plot_h + 60, body)


def outcomes_figure(settled: Counter[int]) -> None:
    """How many distinct end-of-day-six positions settle at each number of coins."""
    left, top, plot_w, plot_h = 60, 50, 620, 210
    low, high = min(settled), max(settled)
    peak = max(settled.values()) * 1.1
    width = plot_w / (high - low + 1)
    body = [title("Every reachable settlement: positions on the last day by settled coins")]
    for coins, count in sorted(settled.items()):
        bar = count / peak * plot_h
        colour = (
            "#d62728" if coins == high else ("#2ca02c" if coins == STARTING_COINS else "#1f77b4")
        )
        body.append(
            f'<rect x="{left + (coins - low) * width:.1f}" y="{top + plot_h - bar:.1f}" width="{max(width - 1, 1):.1f}" height="{bar:.1f}" fill="{colour}"/>'
        )
    for coins in (low, STARTING_COINS, 40, 60, 80, 100, high):
        x = left + (coins - low + 0.5) * width
        body.append(
            f'<text x="{x:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="#444">{coins}</text>'
        )
    body.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#888"/>'
    )
    body.append(
        f'<text x="{left}" y="{top + plot_h + 42}" fill="#444">settled coins; green = never trading ({STARTING_COINS}), red = the best ({high}), leftmost = the worst ({low})</text>'
    )
    svg("outcomes.svg", 720, top + plot_h + 60, body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # values: whole and bounded
    refused = 0
    for bad in (-1, 1.5, "3", True):
        try:
            Coins(bad)  # type: ignore[arg-type]
        except ValueError:
            refused += 1
    value(
        "coins-rejected",
        "coin amounts refused: negative, fractional, text, a truth value (theory 4)",
        refused,
        4,
    )
    refused = 0
    for grain, salt in ((9, 0), (5, 4), (-1, 0), (0, 1.0)):
        try:
            Cargo(grain, salt)  # type: ignore[arg-type]
        except ValueError:
            refused += 1
    value(
        "cargo-rejected",
        "cargos refused: nine of one good, nine in total, negative, fractional (theory 4)",
        refused,
        4,
    )
    value("cargo-capacity", "slots in the hold", CAPACITY, 8)
    refused = 0
    for bad in (0, -2, 2.5):
        try:
            Quote(GRAIN, bad)  # type: ignore[arg-type]
        except ValueError:
            refused += 1
    value("quote-rejected", "prices refused: zero, negative, fractional (theory 3)", refused, 3)
    hold_figure()

    # the market
    value("market-days", "market days", DAYS, 6)
    value(
        "market-low",
        "lowest price in the table",
        min(price(d, g) for d in range(1, 7) for g in Good),
        2,
    )
    value(
        "market-high",
        "highest price in the table",
        max(price(d, g) for d in range(1, 7) for g in Good),
        7,
    )
    value(
        "market-valuation",
        "3 grain and 2 salt valued at day-1 prices, coins (theory 3·3 + 2·5)",
        CargoValuation.value(Cargo(3, 2), MARKET[0]).amount,
        19,
    )
    value(
        "market-same-table",
        "two new sessions see the same six days of quotes (1 = yes)",
        int(all(MARKET[d] is TradingSession("a", d + 1).quotes for d in range(DAYS))),
        1,
    )
    prices_figure()

    # a trade
    session = TradingSession("trade")
    bought = session.buy(GRAIN, 4)
    value(
        "trade-buy-coins",
        "coins after buying 4 grain at 3 from 20 (theory 20 − 12)",
        session.coins.amount,
        8,
    )
    value("trade-buy-cargo", "grain held after that purchase", session.cargo.grain, 4)
    value(
        "trade-event",
        "the TradeExecuted event carries the resulting coins and cargo (1 = yes)",
        int(
            isinstance(bought, TradeExecuted)
            and bought.coins == session.coins
            and bought.cargo == session.cargo
            and bought.price == 3
        ),
        1,
    )
    session.advance()
    session.sell(GRAIN, 2)
    value(
        "trade-sell-coins",
        "coins after selling 2 grain at 4 on day 2 (theory 8 + 8)",
        session.coins.amount,
        16,
    )
    refused = 0
    before = (session.day, session.coins, session.cargo)
    trades: tuple[Callable[[], object], ...] = (
        lambda: session.buy(GRAIN, 0),
        lambda: session.buy(GRAIN, 5),  # 20 coins needed, 16 held
        lambda: session.buy(SALT, 7),  # 2 + 7 > 8 slots (and too dear: coins are checked first)
        lambda: session.sell(GRAIN, 3),
        lambda: session.sell(SALT, 1),
    )
    for attempt in trades:
        try:
            attempt()
        except InvalidTrade:
            refused += 1
    value(
        "trade-refused",
        "invalid trades refused: zero quantity, too dear, too many, two short sales (theory 5)",
        refused,
        5,
    )
    value(
        "trade-refused-unchanged",
        "day, coins and cargo unchanged after those refusals (1 = yes)",
        int(before == (session.day, session.coins, session.cargo)),
        1,
    )
    accepted, short_of_coins, short_of_space = feasible_figure()
    fits = sum(
        1
        for g in range(CAPACITY + 2)
        for s in range(CAPACITY + 2)
        if 2 * g + 6 * s <= 38 and g + s <= CAPACITY
    )
    value(
        "feasible-accepted",
        "day 3 with 38 coins: purchases (grain, salt), 0 to 9 of each, that are accepted, of 100 (theory: 2g + 6s ≤ 38 and g + s ≤ 8)",
        accepted,
        fits,
    )
    value(
        "feasible-refused",
        "of those 100, refused for coins or for cargo space",
        short_of_coins + short_of_space,
        100 - fits,
    )
    value(
        "feasible-coins",
        "of the refused, the session names coins (reported, no theory)",
        short_of_coins,
        short_of_coins,
    )
    value(
        "feasible-space",
        "of the refused, the session names cargo space (reported, no theory)",
        short_of_space,
        short_of_space,
    )

    # worth
    steps, trade_drift, events = play_best()
    value(
        "worth-trade-drift",
        "sum of |change of worth| over the 9 trades of the best plan, coins",
        trade_drift,
        0,
    )
    value(
        "worth-events",
        "events emitted by the best plan: 9 trades, 5 days advanced, 1 settlement",
        events,
        15,
    )
    value("worth-final", "settled coins of the best plan", steps[-1][1], 118)
    nights = [steps[i][2] - steps[i - 1][2] for i in range(1, len(steps)) if steps[i][3]]
    value(
        "worth-night-gain",
        "sum of the six overnight changes of worth in the best plan, coins (theory 118 − 20)",
        sum(nights),
        98,
    )
    worth_figure(steps)

    # days and settlement
    idle = TradingSession("idle")
    days = [idle.day]
    while not idle.settled:
        event = idle.advance()
        if isinstance(event, DayAdvanced):
            days.append(event.day)
    value("days-sequence", "days visited by a session that only advances (theory 6)", len(days), 6)
    value("idle-settles", "settled coins of a session that never trades", idle.coins.amount, 20)
    closed = 0
    actions: tuple[Callable[[], object], ...] = (
        lambda: idle.buy(GRAIN, 1),
        lambda: idle.sell(GRAIN, 1),
        idle.advance,
    )
    for action in actions:
        try:
            action()
        except SessionClosed:
            closed += 1
    value(
        "settled-refuses",
        "actions refused by a settled session: buy, sell, advance (theory 3)",
        closed,
        3,
    )
    holder = TradingSession("holder", DAYS, Coins(4), Cargo(2, 3))
    holder.advance()
    value(
        "settle-liquidation",
        "day 6, 4 coins, 2 grain, 3 salt: settled coins (theory 4 + 2·6 + 3·5)",
        holder.coins.amount,
        31,
    )
    value("settle-empties", "units left in the hold after settlement", holder.cargo.total, 0)

    # the whole game
    states, settled = reachable()
    value(
        "search-states",
        "states (day, coins, grain, salt) reachable through the aggregate",
        states,
        states,
    )
    value("search-best", "largest settled coins over every reachable play", max(settled), 118)
    value(
        "search-worst",
        "smallest settled coins over every reachable play",
        min(settled),
        min(settled),
    )
    value("search-distinct", "distinct settled amounts", len(settled), len(settled))
    history, carried = nightly_greedy()
    value(
        "greedy-final",
        "worth on day 6 when each night carries the largest affordable gain",
        history[-1],
        118,
    )
    value(
        "greedy-matches-search",
        "the nightly rule reaches the searched optimum (1 = yes)",
        int(history[-1] == max(settled)),
        1,
    )
    plan_figure(history, carried)
    outcomes_figure(settled)

    replay = []
    for _ in range(2):
        again = TradingSession("replay")
        again.buy(SALT, 2)
        again.advance()
        again.sell(SALT, 1)
        again.buy(GRAIN, 3)
        replay.append((again.day, again.coins, again.cargo, again.settled))
    value(
        "replay-identical",
        "the same actions give the same session twice (1 = yes)",
        int(replay[0] == replay[1]),
        1,
    )

    lines = [
        "# Measured values",
        "",
        "Written by `make theory-figs` (scripts/theory_figs.py) from the domain itself. Do not edit by hand.",
        "The last column is the relative error; where the theory column is 0 it is the absolute value.",
        "",
        "| id | what is measured | measured | theory | error |",
        "|---|---|---|---|---|",
        *ROWS,
    ]
    (OUT / "values.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
