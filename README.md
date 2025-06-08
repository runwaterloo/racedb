![Python](https://img.shields.io/badge/python-3.13+-blue?logo=python&logoColor=white)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-blueviolet)](https://docs.astral.sh/ruff/)
[![CI](https://gitlab.com/sl70176/racedb/badges/main/pipeline.svg)](https://gitlab.com/sl70176/racedb/-/pipelines)
![coverage](https://gitlab.com/sl70176/racedb/badges/main/coverage.svg)
# RaceDB

## Getting started

These instructions are based on Docker Desktop in WSL/Ubuntu. Adapt as needed.

### Clone the repo
   ```bash
   git clone git@gitlab.com:sl70176/racedb.git;
   cd racedb
   ```

### Copy sample secrets
```bash
cp racedb/secrets.py.sample racedb/secrets.py
```

### Install dependencies
```bash
sudo apt update;
sudo apt install \
  build-essential \
  default-libmysqlclient-dev \
  pkg-config \
  python3-dev
```

###  Setup virtual environmenet
```bash
python3 -m venv .venv;
source .venv/bin/activate;
pip install -r requirements.txt
```

### Setup pre-commit hooks
```bash
pre-commit install
```

### Run tests
```bash
pytest
```

### Start application

```
docker-compose -f deploy/local/docker-compose.yml up --build
```

or to mount local directory into container:

```
docker-compose -f deploy/local/docker-compose-mount-local.yml up --build
```

### Access application

- Racedb: http://localhost:8000/
- Admin interface: http://localhost:8000/admin (admin/admin)

### Add data to database
Option 1: Generate fake data
```bash
deploy/local/loaddata.sh
```

Option 2: Load a dump file
```bash
deploy/local/importdb.sh $DUMP_FILE_PATH
```

### Run tests inside container
This is closer to production, but slower. It uses a running MariaDB database instead of the
in memory SQLite that is normally used for tests.
```
docker exec racedb-web sh -c \
 'DJANGO_SETTINGS_MODULE=racedb.settings.min \
  DISABLE_DEBUG_TOOLBAR=true \
  pytest -v -m "integration or not integration"'
```

## Developer Info

### Pipelines

Add `[push dev]` to a commit message to trigger a pipeline job that pushes the build to https://racedb.runwaterloo.com

Add `[skip ci]` to a commit message to prevent CI from running at all

Add `[full ci]` to a commit message to run the integration tests (in addition to usual testing)

## Configurable Options
The following options can be configured in Configs in the Django admin site.

**email_from_address**: Address that emails will be sent from.

**email_to_address**: Address that emails will be sent to.

**endurrun_same_name**: Configure an ENDURrun athlete to be recognized by multiple names. There can be multiple entries called `endurrun_same_name` in config, but there should only be ONE per human, order doesn't matter. The value should contain a semi-colon separated list of names. e.g.:

```
endurrun_same_name: Sam Lalonde;Jordan Schmidt
endurrun_same_name: Bob Smith;Bobby Smith;Robert Smith
```

**endurrun_stats_min_finishes**: Minimum number of finishes to be included in the ENDURrun finishers section of the ENDURrun Stats view (`/endurrun/stats/`)

**featured_member_id_next**: Member ID to be used next time `update_featured_member_id()` is executed. This will only work for active members with a profile photo. Once used this option will be unset.

**featured_member_tag**: Restrict featured member to ones with this tag.

**homepage_upcoming_exclude_events**: Comma-separated list of events to exclude from homepage Upcoming Events if they would have appeared.
