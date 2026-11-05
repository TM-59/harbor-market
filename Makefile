.PHONY: sync test check serve
sync:
	uv sync --locked --python 3.14
test:
	uv run --locked python scripts/check.py test
check:
	uv run --locked python scripts/check.py check
serve:
	uv run --locked python manage.py runserver localhost:8000 --noreload
