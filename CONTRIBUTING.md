# Contributing to Lemoria

Thanks for considering a contribution. Lemoria is moving from a single-user tool
toward a reusable CLI for AI-assisted development workflows, so reproducibility
and traceability matter as much as code.

## Development setup

```bash
git clone git@github.com:devcristianlopez/lemoria.git
cd lemoria
uv sync --extra dev
uv run pytest -q
uv run ruff check lemoria/ tests/
```

If you do not use `uv`, install editable dependencies with:

```bash
python -m pip install -e ".[dev]"
```

## Before opening a PR

Run the same checks CI runs:

```bash
LEMORIA_ENV=test uv run pytest tests/ --cov=lemoria --cov-report=term-missing
uv run ruff check lemoria/
```

For install or packaging changes, also verify:

```bash
uvx --from build pyproject-build --sdist --wheel
```

## Traceability

Every non-trivial change should be connected to a Lemoria task. Use conventional
commits and include the task trailer in the commit body:

```text
Task: <task-id>
```

After merging or pushing, run:

```bash
lemoria commit sync
lemoria vault sync <project-id>
```

This keeps the chain `PRD -> Task -> Commit -> Vault` navigable.

## Style

- Keep CLI commands explicit and safe; prefer clear errors over tracebacks.
- Do not version private memory (`~/.lemoria/vault`) or local `.env` files.
- Update README/INSTALL/docs when behavior changes.
