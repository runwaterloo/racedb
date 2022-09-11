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

**featured_member_id_next**: Member ID to be used next time `update_featured_member_id()` is executed. This will only work for active members with a profile photo. Once used this option will be unset.

## Misc Developer Info

Adding `[push dev]` to a commit message in a non-main branch will trigger a pipeline job that pushes the build to dev.
