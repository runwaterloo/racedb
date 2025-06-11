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
pip install -r requirements/requirements-dev.txt
```

### Setup pre-commit hooks
```bash
pre-commit install
```

### Start application
```
./deploy/local/start.sh
```
You can add a --rebuild option to rebuild from scatch if needed

### Access application

- Racedb: http://localhost:8000/
- Admin interface: http://localhost:8000/admin (admin/admin)


### Run tests
```bash
pytest
```

### Run tests inside container
This is closer to production, but slower. It uses a running MariaDB database instead of the
in memory SQLite that is normally used for tests.
```bash
docker exec racedb-web pytest
```
### Import a database
```bash
deploy/local/importdb.sh $DUMP_FILE_PATH
```

## Developer Info

### CI Pipelines

There are 5 different pipeline steps that may execute depending on the situation.

**test**: always executes

**build-test-push**: executes when the branch is main, or the commit message contains `[push dev]`

**integration-test**: executes when `Dockerfile` or `requirements/requirements.txt` have changes, or the commit message contains `[full ci]`

**tag-commit**: executes on the main branch only, when previous steps were successful

**update-dependencies**: executes when the `UPDATE_DEPENDENCIES` variable is set to `true`

Add `[push dev]` to a commit message to pushes the build to https://racedb.runwaterloo.com

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

## REST API

The REST API provides programmatic access to results. The API is available at:

    https://api.runwaterloo.com/v1/

### Authentication

All API endpoints require authentication. If you access the API in a browser and are not authenticated, the response will include a `login_url` field to direct you to the login page. For programmatic access, you must include your authentication token in the `Authorization` header:

```
Authorization: Token <your_token>
```

Hit someone up for an account and API token if needed.

### Available Endpoints

The API is under active development. Some endpoints (such as teams and splits) are not yet implemented, but the core event and result data is available.

#### Events Endpoint

The main entry point is the events endpoint:

    GET /v1/events/

Returns a list of events, sorted by date (most recent first). Each event includes denormalized fields for easy frontend use, and a link to the results for that event.

Example Response
```
coming soon
```

##### Filtering Events

You can filter events using the following query parameters:

- `year`: Filter by event year (e.g., `?year=2024`)
- `race_slug`: Filter by race slug (e.g., `?race_slug=endurrun`)
- `distance_slug`: Filter by distance slug (e.g., `?distance_slug=marathon`)
- `results_exist`: Filter by whether results exist for the event (`true` or `false`)

You can combine filters as needed. Example:

```
GET /v1/events/?year=2024&race_slug=endurrun&results_exist=true
```

##### Pagination

Responses are paginated with a page size of 50 items. Each response includes `count`, `next`, and `previous` fields:

- `count`: Total number of items matching your query.
- `next`: URL to fetch the next page of results (or `null` if there are no more pages).
- `previous`: URL to fetch the previous page (or `null` if you are on the first page).

##### Example Response

### Results Link

Each event includes a `results_url` field. You can use this to fetch results for that event:

```
GET /v1/events/<event_id>/results/
```

#### Example Response

```
coming soon
```

### Notes

- The API is evolving. Some endpoints (e.g., teams, splits) are not yet available.
- All date and time fields are in ISO 8601 format (UTC).
- If you have questions or need additional endpoints, please contact the maintainers.
