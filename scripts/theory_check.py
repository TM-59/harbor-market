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


def _rows(index: str, errors: list[str]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in index.splitlines():
        found = ROW.match(line)
        if found:
            rows[found.group(1)] = {
                "page": found.group(3),
                "figure": found.group(4),
                "code": found.group(5),
                "test": found.group(6),
            }
    if not rows:
        errors.append("coverage table not found in docs/theory/README.md")
    return rows


def _sections(pages: dict[str, str]) -> dict[str, tuple[str, str]]:
    sections: dict[str, tuple[str, str]] = {}
    for name, text in pages.items():
        for head in re.finditer(r"^## (S\d\d) — .*$", text, flags=re.MULTILINE):
            end = text.find("\n## ", head.end())
            sections[head.group(1)] = (name, text[head.end() : end if end > 0 else len(text)])
    return sections


def _figure_errors(sid: str, body: str, row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
    has_mermaid = "```mermaid" in body
    if not images and not has_mermaid:
        errors.append(f"{sid}: no figure (neither an image nor a mermaid diagram)")
    errors.extend(
        f"{sid}: figure {image} does not exist (run make theory-figs)"
        for image in images
        if not (THEORY / image).is_file()
    )
    if "mermaid" in row["figure"] and not has_mermaid:
        errors.append(f"{sid}: table says mermaid, section has none")
    errors.extend(
        f"{sid}: table lists {figure}, the section does not show it"
        for figure in re.findall(r"`(figures/[^`]+)`", row["figure"])
        if figure not in images
    )
    return errors


def _reference_errors(sid: str, row: dict[str, str], values: str) -> list[str]:
    errors: list[str] = []
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
    return errors


def _statement_errors(
    rows: dict[str, dict[str, str]], sections: dict[str, tuple[str, str]], values: str
) -> list[str]:
    errors: list[str] = []
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
        errors.extend(_figure_errors(sid, body, row))
        positions = [body.find(f"**{part}") for part in PARTS]
        if min(positions) < 0 or positions != sorted(positions):
            errors.append(f"{sid}: needs Statement, Assumptions, Derivation, Code, Tests in order")
        errors.extend(_reference_errors(sid, row, values))
    return errors


def _page_errors(pages: dict[str, str], index: str, values: str) -> list[str]:
    errors = [
        f"{name}: quotes value `{key}` that figures/values.md does not have"
        for name, text in pages.items()
        for key in re.findall(r"`([a-z]+(?:-[a-z0-9.]+)+)`", text)
        if f"`{key}`" not in values and not key.startswith("make")
    ]
    errors.extend(
        f"{name}: broken link {target}"
        for name, text in {**pages, "README.md": index}.items()
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text)
        if "://" not in target and not (THEORY / target).exists()
    )
    return errors


def _export_errors(mentioned: set[str]) -> list[str]:
    init = next((ROOT / "src").glob("*/domain/__init__.py"))
    return [
        f"domain: exported name {exported} is in neither table of the index"
        for exported in re.findall(
            r'^    "([A-Za-z_]+)",$', init.read_text(encoding="utf-8"), flags=re.MULTILINE
        )
        if exported not in mentioned
    ]


def main() -> int:
    """Check every statement, figure, link and reference; print the result."""
    index = (THEORY / "README.md").read_text(encoding="utf-8")
    pages = {p.name: p.read_text(encoding="utf-8") for p in sorted(THEORY.glob("0*.md"))}
    values = (THEORY / "figures/values.md").read_text(encoding="utf-8")

    errors: list[str] = []
    rows = _rows(index, errors)
    errors.extend(_statement_errors(rows, _sections(pages), values))
    errors.extend(_page_errors(pages, index, values))
    mentioned = {token.rstrip("(") for _, token in refs(index)}
    errors.extend(_export_errors(mentioned))

    if errors:
        sys.stdout.write("\n".join(errors) + "\n")
        sys.stdout.write(f"theory-check: {len(errors)} problem(s)\n")
        return 1
    figures = sum(1 for _ in THEORY.glob("figures/*.svg"))
    sys.stdout.write(
        f"theory-check: OK ({len(rows)} statements, each with a figure; {figures} generated "
        f"figures; {len(mentioned)} functions/tests/values referenced)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
