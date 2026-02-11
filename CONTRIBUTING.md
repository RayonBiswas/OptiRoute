# Contributing to OptiRoute

Thanks for your interest in improving OptiRoute. Please follow these guidelines to keep the project healthy and reviewable.

1. Code style
   - Python: follow PEP8. Prefer modern typing and small functions.
   - JavaScript/TypeScript: follow existing project conventions.

2. Branches & PRs
   - Create a feature branch from `main`: `git checkout -b feat/short-description`.
   - Open a pull request with a clear description and testing notes.

3. Tests & CI
   - Add unit tests for backend logic where possible.
   - CI will run a dependency install smoke test; include lightweight tests in future iterations.

4. Commits
   - Keep commits small and focused. Use imperative messages: `Fix`, `Add`, `Refactor`.

5. Security
   - Do not commit secrets. Add keys to `.env` and ensure `.gitignore` excludes it.

6. Automation
   - Pre-commit hooks are recommended. A template `.pre-commit-config.yaml` is included.
