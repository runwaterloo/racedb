# Contributing to RaceDB

Thank you for your interest in contributing to RaceDB! We welcome all contributions, whether they are bug reports, feature requests, code improvements, or documentation updates.

## Getting Started
- Please see the [README.md](./README.md) for setup instructions, running the application, and running tests.
- If you have questions, open an issue or reach out to the maintainers.

## Code Style & Linting
- **Python code** must pass [ruff](https://docs.astral.sh/ruff/) checks. Run `ruff check .` before submitting a PR.
- **Templates** should be formatted with [djlint](https://djlint.com/). Run `djlint .` to check formatting.
- Please use [pre-commit](https://pre-commit.com/) hooks: `pre-commit install` after cloning.

## Commit Messages
- Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commit messages.
- Valid types:
  - **feat**: New feature
  - **fix**: Bug fix
  - **chore**: Maintenance tasks (dependencies, build process, tooling, etc)
  - **docs**: Documentation only changes
  - **test**: Adding or correcting tests
- Start with a lowercase letter
- Be written in the imperative mood (e.g., "add", "fix", "update"), as if completing the sentence: "When merged, this commit will ..."
- Examples:
  - `feat: add a new thing`
  - `fix: correct typo in user model`
  - `chore(deps): bump somepackage from 1.2 to 1.3`
- This helps automate changelogs and release notes.

## Pull Requests
- Make sure your branch is up to date with `main` before opening a PR.
- All PRs are tested with GitHub Actions. Please ensure your changes pass all checks.
- Add tests for new features or bug fixes when possible.
- Keep PRs focused and small; large or unrelated changes may be asked to be split up.

## Reporting Issues
- Please provide as much detail as possible, including steps to reproduce, expected behavior, and screenshots/logs if relevant.

---
Thank you for helping make RaceDB better!
