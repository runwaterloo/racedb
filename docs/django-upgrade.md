# Django Minor Version Upgrade Procedure

This guide describes the recommended steps for safely upgrading Django and related dependencies in this project.

## 1. Review Django Release Notes
- Before making any changes, review the [Django release notes](https://docs.djangoproject.com/en/stable/releases/) for the target version.
- Identify any breaking changes, deprecations, or manual code changes required.

## 2. Update django-upgrade Version
- Edit `pyproject.toml` to set the desired (minor) version of `django-upgrade`.

## 3. Update Requirements
- Update `requirements/requirements.txt` to match the new Django version.

## 4. Install Updated Requirements
```bash
pip install -r requirements/requirements-dev.txt
```

## 5. Run django-upgrade
- Use pre-commit to automatically apply code upgrades for the new Django version:
```bash
pre-commit run django-upgrade --all-files
```
- Review and commit any changes made by `django-upgrade`.

## 6. Run Tests
- Ensure all tests pass after the upgrade:
```bash
pytest
```
- Fix any issues or deprecations that arise.

## 7. Push a Branch

- Commit your changes to a new branch, prefix commit message with `chore(deps):`
- Example commit message: `chore(deps): bump Django from 1.2.3 to 1.3.4. Fixes #567`
- Push the branch to GitHub

## 8. Create Pull Request

- Create a pull request
- Confirm all checks pass

## 9. Merge and Deploy

- Merge your pull request

This will automatically trigger a GitHub action that creates a release, and RRW will pick it up within a few minutes.

---

**Tip:** Always perform upgrades in a feature branch and use CI to validate changes before merging to main.
