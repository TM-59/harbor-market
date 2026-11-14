"""Bounded local checks; keep native JUnit and record failures as well as passes."""

import json
import os
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

started = datetime.now(UTC)
clock = time.monotonic()
run_id = started.strftime("%Y%m%dT%H%M%S%fZ")
folder = Path("test-results") / run_id
folder.mkdir(parents=True)
mode = sys.argv[1]
if mode not in {"test", "check"}:
    raise SystemExit("expected test or check")
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
check_commands = (
    [
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
        ["mypy"],
        ["lint-imports", "--no-cache"],
        [sys.executable, "manage.py", "check"],
        [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
    ]
    if mode == "check"
    else []
)
commands = [*test_commands, *check_commands]
results = []
durations = []
for command in commands:
    while os.getloadavg()[0] > 20:
        time.sleep(5)
    command_started = time.monotonic()
    try:
        result = subprocess.run(command, timeout=60, check=False)
        results.append(result.returncode)
    except subprocess.TimeoutExpired, OSError:
        results.append(124)
    durations.append(round(time.monotonic() - command_started, 3))
suite_counts = []
counts = dict(tests=0, failures=0, errors=0, skipped=0)
for index, (kind, requirements, _) in enumerate(test_suites):
    junit = folder / f"{kind}-pytest.xml"
    suite_count = dict(tests=0, failures=0, errors=0, skipped=0)
    if junit.exists():
        for case in ET.parse(junit).iter("testcase"):
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
        dict(
            kind=kind,
            framework="pytest",
            command=test_commands[index],
            status="pass" if results[index] == 0 and suite_count["tests"] else "fail",
            duration_seconds=durations[index],
            counts=suite_count,
            junit=str(junit) if junit.exists() else None,
            requirements=requirements,
            reason="test process timed out or failed to start" if results[index] == 124 else None,
        )
    )
status = "pass" if not any(results) and counts["tests"] else "fail"
git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
dirty = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
).stdout
summary = dict(
    schema_version=1,
    run_id=run_id,
    repository="TM-59/harbor-market",
    commit=git.stdout.strip(),
    dirty=bool(dirty),
    started_at=started.isoformat(),
    finished_at=datetime.now(UTC).isoformat(),
    duration_seconds=round(time.monotonic() - clock, 3),
    status=status,
    exit_code=0 if status == "pass" else 1,
    environment=dict(
        os=platform.system(),
        architecture=platform.machine(),
        tools={"python": platform.python_version()},
        jobs=1,
        seed=None,
    ),
    counts=counts,
    coverage=dict(
        status="not_measured",
        line_percent=None,
        branch_percent=None,
        reason="M3 persistence; coverage measurement remains deferred.",
    ),
    metrics=[
        dict(
            name=f"check_{index}_exit",
            status="pass" if code == 0 else "fail",
            value=code,
            unit="exit_code",
            threshold=0,
            comparison="eq",
            reason="check timed out or failed to start" if code == 124 else None,
        )
        for index, code in enumerate(results[len(test_commands) :], 1)
    ],
    suites=suite_counts,
)
text = json.dumps(summary, indent=2) + "\n"
(folder / "summary.json").write_text(text)
Path("test-results/summary.json").write_text(text)
raise SystemExit(summary["exit_code"])
