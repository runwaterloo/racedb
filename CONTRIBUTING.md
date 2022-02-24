## Versions and main branch
The pipeline requires that you bump version.txt when committing to main. If you are making trivial changes that don't impact the application in any way you can add `[skip ci]` to the commit message and not update version.txt. This will prevent the pipeline (and deployment) from running at all.

## Formatting and Linting

This project has a pre-commit hook that formats with black and lints with flake8. You will need to be using at least Python 3.7, and have these packages installed. On Debian 10 for example:
```
apt-get update
apt install python3-pip
pip3 install black flake8 pre-commit
```

To initially install pre-commit into the repo this was done:
```
pre-commit install
```
