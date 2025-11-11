# Repository Guidelines

## Project Structure & Module Organization
- Main Package (`cforge/`): CLI for Context Forge (entry `main.py`)
- Commands (`cforge/commands/`): Individual CLI command sections
- Tests (`tests`): structure mirrors `cforge`

## Coding Style & Naming Conventions
- Python >= 3.11. Type hints required; strict `mypy` settings.
- Formatters/linters: Black (line length 200), isort (profile=black), Ruff (F,E,W,B,ASYNC), Pylint as configured in `pyproject.toml` and dotfiles.
- Naming: `snake_case` for modules/functions, `PascalCase` for classes, `UPPER_CASE` for constants.
- Group imports per isort sections (stdlib, third-party, first-party `mcpgateway`, local).

## Testing Guidelines
- Pytest with async; discovery configured in `pyproject.toml`.
- Layout: follow the structure of the `cforge` package.
- Naming: files `test_*.py`, classes `Test*`, functions `test_*`.
- Commands: `make test`, `pytest -k "name"`. Use `make coverage` for reports.
- Keep tests deterministic, isolated, and fast by default.

## Commit & Pull Request Guidelines
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`). Link issues (e.g., `Closes #123`).
- Sign every commit with DCO: `git commit -s`.
- Do not mention Claude or Claude Code in PRs/diffs. Do not include effort estimates or "phases".
- Include tests and docs for behavior changes.
- Require green lint and tests locally before opening a PR.

## Security & Configuration Tips
- Copy `.env.example` → `.env`; verify with `make check-env`. Never commit secrets.
