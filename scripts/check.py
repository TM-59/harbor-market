"""Bounded local checks; keep native JUnit and record failures as well as passes."""

import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from defusedxml import ElementTree

LOAD_LIMIT = 20  # wait while the machine's one-minute load average is above this
TIMED_OUT = 124  # exit code recorded when a step times out or cannot start
STEP_SECONDS = 60

started = datetime.now(UTC)
clock = time.monotonic()
run_id = started.strftime("%Y%m%dT%H%M%S%fZ")
folder = Path("test-results") / run_id
folder.mkdir(parents=True)
mode = sys.argv[1]
if mode not in {"test", "check"}:
    message = "expected test or check"
    raise SystemExit(message)
test_suites = [
    (
        "unit",
        [
            "REQ-HEALTH",
            "REQ-CORE",
            "REQ-VALUE",
            "REQ-TRADE",
            "REQ-DAY",
            "REQ-USECASE",
        ],
        ["-m", "not integration"],
    )
]
if mode == "check":
    test_suites.append(
        (
            "integration",
            ["REQ-PERSISTENCE", "REQ-REVISION", "REQ-ATOMIC"],
            ["-m", "integration"],
        )
    )
test_commands = [
    [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *selection,
        f"--junitxml={folder / f'{kind}-pytest.xml'}",
    ]
    for kind, _, selection in test_suites
]


def _junit_env(kind: str) -> dict[str, str]:
    """Return the environment that makes pytest write the `kind` JUnit report."""
    return {**os.environ, "PYTEST_ADDOPTS": f"--junitxml={folder / f'{kind}-pytest.xml'}"}


# Each step is spelled out as a literal command so that what runs is visible in one place.
Step = Callable[[], subprocess.CompletedProcess[bytes]]
steps: list[Step] = [
    lambda: subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "not integration"],
        env=_junit_env("unit"),
        timeout=STEP_SECONDS,
        check=False,
    )
]
if mode == "check":
    steps += [
        lambda: subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-m", "integration"],
            env=_junit_env("integration"),
            timeout=STEP_SECONDS,
            check=False,
        ),
        lambda: subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."], timeout=STEP_SECONDS, check=False
        ),
        lambda: subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", "."],
            timeout=STEP_SECONDS,
            check=False,
        ),
        lambda: subprocess.run([sys.executable, "-m", "mypy"], timeout=STEP_SECONDS, check=False),
        lambda: subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; from importlinter.cli import lint_imports_command; "
                    "sys.exit(lint_imports_command())"
                ),
                "--no-cache",
            ],
            timeout=STEP_SECONDS,
            check=False,
        ),
        lambda: subprocess.run(
            [sys.executable, "manage.py", "check"], timeout=STEP_SECONDS, check=False
        ),
        lambda: subprocess.run(
            [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
            timeout=STEP_SECONDS,
            check=False,
        ),
    ]
results = []
durations = []
for step in steps:
    while os.getloadavg()[0] > LOAD_LIMIT:
        time.sleep(5)
    command_started = time.monotonic()
    try:
        results.append(step().returncode)
    except subprocess.TimeoutExpired, OSError:
        results.append(TIMED_OUT)
    durations.append(round(time.monotonic() - command_started, 3))
suite_counts = []
counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
for index, (kind, requirements, _) in enumerate(test_suites):
    junit = folder / f"{kind}-pytest.xml"
    suite_count = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    if junit.exists():
        for case in ElementTree.parse(junit).iter("testcase"):
            suite_count["tests"] += 1
            for node, key in [
                ("failure", "failures"),
                ("error", "errors"),
                ("skipped", "skipped"),
            ]:
                suite_count[key] += int(case.find(node) is not None)
    for key in counts:
        counts[key] += suite_count[key]
    suite_counts.append(
        {
            "kind": kind,
            "framework": "pytest",
            "command": test_commands[index],
            "status": "pass" if results[index] == 0 and suite_count["tests"] else "fail",
            "duration_seconds": durations[index],
            "counts": suite_count,
            "junit": str(junit) if junit.exists() else None,
            "requirements": requirements,
            "reason": "test process timed out or failed to start"
            if results[index] == TIMED_OUT
            else None,
        }
    )
status = "pass" if not any(results) and counts["tests"] else "fail"
git = subprocess.run(
    ["/usr/bin/git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
)
dirty = subprocess.run(
    ["/usr/bin/git", "status", "--porcelain"], capture_output=True, text=True, check=True
).stdout
summary = {
    "schema_version": 1,
    "run_id": run_id,
    "repository": "TM-59/harbor-market",
    "commit": git.stdout.strip(),
    "dirty": bool(dirty),
    "started_at": started.isoformat(),
    "finished_at": datetime.now(UTC).isoformat(),
    "duration_seconds": round(time.monotonic() - clock, 3),
    "status": status,
    "exit_code": 0 if status == "pass" else 1,
    "environment": {
        "os": platform.system(),
        "architecture": platform.machine(),
        "tools": {"python": platform.python_version()},
        "jobs": 1,
        "seed": None,
    },
    "counts": counts,
    "coverage": {
        "status": "not_measured",
        "line_percent": None,
        "branch_percent": None,
        "reason": "M3 persistence; coverage measurement remains deferred.",
    },
    "metrics": [
        {
            "name": f"check_{index}_exit",
            "status": "pass" if code == 0 else "fail",
            "value": code,
            "unit": "exit_code",
            "threshold": 0,
            "comparison": "eq",
            "reason": "check timed out or failed to start" if code == TIMED_OUT else None,
        }
        for index, code in enumerate(results[len(test_commands) :], 1)
    ],
    "suites": suite_counts,
}
text = json.dumps(summary, indent=2) + "\n"
(folder / "summary.json").write_text(text)
Path("test-results/summary.json").write_text(text)
raise SystemExit(summary["exit_code"])
