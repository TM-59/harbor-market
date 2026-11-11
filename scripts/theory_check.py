"""Checks docs/theory against the code. Run with `make theory-check`. Standard library only.

Fails when a statement has no section or no figure, a link or figure is missing, a
referenced function, test or measured value is gone, or a name exported by the domain
appears in neither table of the index.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEORY = ROOT / "docs/theory"
FIGS = "scripts/theory_figs.py"
ROW = re.compile(r"\| (S\d\d) \| (.+?) \| \[\d\]\(([^)]+)\) \| (.+?) \| (.+?) \| (.+?) \|$")
PARTS = ("Statement.", "Assumptions", "Derivation.", "Code.", "Tests.")


def refs(cell: str) -> list[tuple[str, str]]:
    return re.findall(r"`([^`#\s]+)#([^`\n]+)`", cell)


def main() -> int:
    errors: list[str] = []
    index = (THEORY / "README.md").read_text(encoding="utf-8")
    pages = {p.name: p.read_text(encoding="utf-8") for p in sorted(THEORY.glob("0*.md"))}
    values = (THEORY / "figures/values.md").read_text(encoding="utf-8")

    rows: dict[str, dict[str, str]] = {}
    for line in index.splitlines():
        found = ROW.match(line)
        if found:
            rows[found.group(1)] = dict(
                page=found.group(3), figure=found.group(4), code=found.group(5), test=found.group(6)
            )
    if not rows:
        errors.append("coverage table not found in docs/theory/README.md")

    sections: dict[str, tuple[str, str]] = {}
    for name, text in pages.items():
        for head in re.finditer(r"^## (S\d\d) — .*$", text, flags=re.M):
            end = text.find("\n## ", head.end())
            sections[head.group(1)] = (name, text[head.end() : end if end > 0 else len(text)])

    for sid in sorted(set(rows) | set(sections)):
        if sid not in rows:
            errors.append(f"{sid}: section exists but is missing from the coverage table")
            continue
        if sid not in sections:
            errors.append(f"{sid}: in the coverage table but has no section")
            continue
        name, body = sections[sid]
        row = rows[sid]
        if row["page"] != name:
            errors.append(f"{sid}: table says {row['page']}, section is in {name}")
        images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
        has_mermaid = "```mermaid" in body
        if not images and not has_mermaid:
            errors.append(f"{sid}: no figure (neither an image nor a mermaid diagram)")
        for image in images:
            if not (THEORY / image).is_file():
                errors.append(f"{sid}: figure {image} does not exist (run make theory-figs)")
        if "mermaid" in row["figure"] and not has_mermaid:
            errors.append(f"{sid}: table says mermaid, section has none")
        for figure in re.findall(r"`(figures/[^`]+)`", row["figure"]):
            if figure not in images:
                errors.append(f"{sid}: table lists {figure}, the section does not show it")
        positions = [body.find(f"**{part}") for part in PARTS]
        if min(positions) < 0 or positions != sorted(positions):
            errors.append(f"{sid}: needs Statement, Assumptions, Derivation, Code, Tests in order")
        for cell in (row["code"], row["test"]):
            if not refs(cell):
                errors.append(f"{sid}: a code/test cell has no `file#token` reference")
            for file, token in refs(cell):
                path = ROOT / file
                if not path.is_file():
                    errors.append(f"{sid}: {file} does not exist")
                elif file == FIGS:
                    if f'"{token}"' not in path.read_text(encoding="utf-8"):
                        errors.append(f"{sid}: measured value {token} is not produced by {FIGS}")
                    elif f"`{token}`" not in values:
                        errors.append(f"{sid}: measured value {token} is not in values.md")
                elif token not in path.read_text(encoding="utf-8"):
                    errors.append(f"{sid}: {token} is no longer in {file}")

    for name, text in pages.items():
        for key in re.findall(r"`([a-z]+(?:-[a-z0-9.]+)+)`", text):
            if f"`{key}`" not in values and not key.startswith("make"):
                errors.append(f"{name}: quotes value `{key}` that figures/values.md does not have")

    for name, text in {**pages, "README.md": index}.items():
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
            if "://" not in target and not (THEORY / target).exists():
                errors.append(f"{name}: broken link {target}")

    mentioned = {token.rstrip("(") for _, token in refs(index)}
    init = next((ROOT / "src").glob("*/domain/__init__.py"))
    for exported in re.findall(
        r'^    "([A-Za-z_]+)",$', init.read_text(encoding="utf-8"), flags=re.M
    ):
        if exported not in mentioned:
            errors.append(f"domain: exported name {exported} is in neither table of the index")

    if errors:
        print("\n".join(errors))
        print(f"theory-check: {len(errors)} problem(s)")
        return 1
    figures = sum(1 for _ in THEORY.glob("figures/*.svg"))
    print(
        f"theory-check: OK ({len(rows)} statements, each with a figure; {figures} generated "
        f"figures; {len(mentioned)} functions/tests/values referenced)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
