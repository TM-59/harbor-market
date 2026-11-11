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
junit = folder / "unit-pytest.xml"
mode = sys.argv[1]
if mode not in {"test", "check"}:
    raise SystemExit("expected test or check")
commands = [[sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}"]]
if mode == "check":
    commands += [
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
        ["mypy"],
        ["lint-imports", "--no-cache"],
        [sys.executable, "manage.py", "check"],
    ]
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
counts = dict(tests=0, failures=0, errors=0, skipped=0)
if junit.exists():
    for case in ET.parse(junit).iter("testcase"):
        counts["tests"] += 1
        for node, key in [("failure", "failures"), ("error", "errors"), ("skipped", "skipped")]:
            counts[key] += int(case.find(node) is not None)
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
        reason="M1 scaffold; coverage measurement is deferred.",
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
        for index, code in enumerate(results[1:], 1)
    ],
    suites=[
        dict(
            kind="unit",
            framework="pytest",
            command=commands[0],
            status="pass" if results[0] == 0 and counts["tests"] else "fail",
            duration_seconds=durations[0],
            counts=counts,
            junit=str(junit) if junit.exists() else None,
            requirements=["REQ-HEALTH", "REQ-CORE", "REQ-VALUE", "REQ-TRADE", "REQ-DAY"],
            reason="unit process timed out or failed to start" if results[0] == 124 else None,
        )
    ],
)
text = json.dumps(summary, indent=2) + "\n"
(folder / "summary.json").write_text(text)
Path("test-results/summary.json").write_text(text)
raise SystemExit(summary["exit_code"])
