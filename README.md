[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
# RaceDB

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

## Local development

```
cd deploy/local
docker-compose up --build
```

This will bring up MariaDB and run `migrate` which will create the schema. 

Racedb should be available at http://localhost:8000/

Note: This is still a WIP and things are very broken without actual data in the tables. Until we generate fake data, the main page will give an error. You can see things kind of working-ish at http://localhost:8000/events .

Django admin interface is available at http://localhost:8000/admin

Optionally populate the database with:

```
./loaddata.sh
```

Tests can be run locally with:

```
docker exec racedb-web ./manage.py test --settings=racedb.settings.min
```

## Misc Developer Info

Adding `[push dev]` to a commit message in a non-main branch will trigger a pipeline job that pushes the build to dev.
