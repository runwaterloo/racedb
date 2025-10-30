![Python](https://img.shields.io/badge/python-3.13+-blue?logo=python&logoColor=white)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-blueviolet)](https://docs.astral.sh/ruff/)
[![Template style: djlint](https://img.shields.io/badge/template%20style-djlint-yellowgreen)](https://djlint.com/)
[![Unit Tests](https://github.com/runwaterloo/racedb/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/runwaterloo/racedb/actions/workflows/unit-tests.yml)
[![codecov](https://codecov.io/github/runwaterloo/racedb/graph/badge.svg?token=4NK7NXXBAP)](https://codecov.io/github/runwaterloo/racedb)
# RaceDB

## Getting started on Codespaces

The fastest way to get started is with GitHub Codespaces.

1. Click the green "Code" button on GitHub, click Codespaces, Create codespace on main
2. **Don't touch anything** until the terminal says "Finsihed configuring codespace. Press any key to exit.", it will take a while
3. Press any key to get to a prompt, then type `./deploy/local/start.sh`
4. Wait a few minutes for the build to complete, you'll see "STARTUP COMPLETE!"
6. Click on PORTS, 8000, 🌐 (Open in Browser)

You now have your own development version of RaceDB running, you can edit code and it will be reflected on your site.

If you need to rebuild the environment run `./deploy/local/start.sh --rebuild` in the terminal

### Codespaces tips & reminders

- **Push your changes:** Always push your branches and commits to GitHub before stopping or deleting a Codespace. Unsaved work will be lost when a Codespace is deleted.
- **Close unused Codespaces:** Delete or stop Codespaces you are no longer using to free up resources and avoid hitting your usage quota.
- **Check your usage:** You can view your Codespaces usage and manage active environments at [github.com/codespaces](https://github.com/codespaces) or via the "Codespaces" tab on your GitHub profile.

---

## Getting started locally

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
This is closer to production, but slower. It uses a running PostgreSQL database instead of the
in memory SQLite that is normally used for tests.
```bash
docker exec racedb-web pytest
```
### Import a database
```bash
deploy/local/importdb.sh $DUMP_FILE_PATH
```

## Developer Info

### GitHub Actions

There are different workflows that may execute depending on the situation.

**Unit Tests**:

- always

**Main Pipline**:

- main branch only
- includes Unit Tests
- also build image, tags image, tags commit, creates GitHub release
- can be skipped with `[skip build]` in commit message

**Build and Push Docker Image**

- pushes an image without creating a release, useful for pushing to dev
- must be [triggered manually](https://github.com/runwaterloo/racedb/actions/workflows/docker-build-push.yml)

**Integration Tests**:

- any commit where Dockefile or requirements/* have changed
- can be [triggered manually](https://github.com/runwaterloo/racedb/actions/workflows/integration-tests.yml)

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

[https://api.runwaterloo.com/v1/](https://api.runwaterloo.com/v1/)

### Authentication

All API endpoints require authentication. If you access the API in a browser and are not authenticated, the response will include a `login_url` field to direct you to the login page. For programmatic access, you must include your authentication token in the `Authorization` header:

```
Authorization: Token <your_token>
```

Hit someone up for an account and API token if needed.

### Events Endpoint

The main entry point is the events endpoint:

    GET /v1/events/

Returns a list of events, sorted by date (most recent first). Each event includes denormalized fields for easy frontend use, and a link to the results for that event.

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

#### Results Link

Each event includes a `results_url` field. You can use this to fetch results for that event:

```
GET /v1/events/<event_id>/results/
```
### Pagination

Responses from all endpointsare paginated with a page size of 50 items. Each response includes `count`, `next`, and `previous` fields:

- `count`: Total number of items matching your query.
- `next`: URL to fetch the next page of results (or `null` if there are no more pages).
- `previous`: URL to fetch the previous page (or `null` if you are on the first page).


### Notes

- The API is evolving. Some endpoints (e.g., teams, splits) are not yet available.
- All date and time fields are in ISO 8601 format (UTC).
- If you have questions or need additional endpoints, please contact the maintainers.
