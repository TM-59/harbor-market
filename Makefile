.PHONY: sync test check serve theory-figs theory-check
sync:
	uv sync --locked --python 3.14
test:
	uv run --locked python scripts/check.py test
check:
	uv run --locked python scripts/check.py check
serve:
	uv run --locked python manage.py runserver localhost:8000 --noreload
# Regenerates the drawn figures and the measured-values table of docs/theory (one command).
theory-figs:
	uv run --locked python scripts/theory_figs.py docs/theory/figures
# Fails when a statement of docs/theory has no figure, a link is broken, or a referenced name is gone.
theory-check:
	uv run --locked python scripts/theory_check.py
