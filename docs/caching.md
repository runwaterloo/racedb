# Cache and invalidation

## Cache invalidation in plain language

Pages on this site (the homepage, and event pages for events in the past 30 days) are served from a cache so they load fast. When something changes, the cache is refreshed automatically — you don't need to do anything.

| If you do this... | The site shows the change... |
|---|---|
| Add or change results (add races) | Immediately |
| Use the cache-clearing endpoint | Immediately |
| Deploy a new version of the site | Right after it restarts |
| Change anything else (admin edits, scripts, photo updates, psql) | Within one minute |

The "within one minute" part is an automatic checker that looks at the database every minute. When it sees that anything has changed, it refreshes the site. In normal operation the delay is at most a minute, and most changes are immediate because they flow through the site itself.

If a change doesn't appear within a minute or two, that's a bug: report it with

1. the exact time you made the change,
2. what you changed and where,
3. the page where you saw stale content,
4. whether a hard refresh (Ctrl+Shift+R) still showed it stale.

## How it works

### Generation-based invalidation

The cache stores each rendered page under its key (for example `index.` or `event.1495.filter=M35-39`) as a tuple of `(generation, value)`. A single global counter, `cache_generation`, lives in Redis alongside them.

- **Read** (`shared/cache_lock.get_or_render`): read the current generation, fetch the entry. It's a hit only if the entry's stored generation equals the current one. Otherwise it's a miss and the page re-renders.
- **Render**: render under a single-flight lock (concurrent misses share one render). The finished page is stamped with the generation read *at the start of the render* and stored with a 30-hour TTL.
- **Invalidate** (`bump_generation()`): increment the counter. No entries are touched, but every entry instantly becomes stale because its generation no longer matches. The next request re-renders and stores the new generation.

Why not `cache.clear()`? Clearing has a race: a render that started before the clear can finish after it and write pre-clear content into the now-empty cache, which then reads as a fresh hit for up to its TTL. Stamping entries with the generation read at render start kills that race — a late write is immediately recognized as stale.

The 30-hour TTL is a safety net only. Normal invalidation happens long before it, because the daily `update_featured_member_id` job writes to the database and triggers the watcher.

### Invalidation paths

| Path | Mechanism | Latency |
|---|---|---|
| `db_cache_watcher` (celery beat, every minute) | Compares a `pg_stat_user_tables` fingerprint over `racedbapp_%` tables against the previous run; a difference bumps the generation | ≤ 60 s |
| `config_post_save` signal (any Config saved, including in admin) | Enqueues `clear_cache` | Immediate |
| `addraces` command (results added or changed) | Enqueues `clear_cache` | Immediate |
| `/clearcache` view and `clear_cache` / `bump_cache_generation` management commands | Enqueue `clear_cache` | Immediate |
| Deploy webhook | Enqueues `clear_cache`, then touches `.restart` | After restart |

`clear_cache` bumps the generation and enqueues `warm_cache`, which re-renders the hot pages so visitors get cache hits instead of cold renders. It is idempotent, and because the Celery broker is Redis, an enqueued warm survives the post-deploy worker restart (it is redelivered after startup, warming with the newly deployed code).

### Watcher details

Every minute (celery beat), `db_cache_watcher` runs a cheap fingerprint query:

```sql
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables WHERE relname LIKE 'racedbapp_%'
```

This counts inserts, updates and deletes per table since the database last had its statistics reset. Comparing the snapshot to the previous run's snapshot shows whether anything in a `racedbapp_%` table changed. Framework tables (`django_session`, `django_admin_log`, `django_migrations`) are deliberately excluded: session churn and admin *browsing* are not cache-worthy, and admin saves always touch a `racedbapp` table anyway. The watcher is also the safety net for changes the app's signals can't see — bulk operations, raw SQL, external writers such as the photo updater.

Knobs (Configs in the Django admin):

| Config | Default | Purpose |
|---|---|---|
| `cache_watcher_dry_run` | `false` | `true`: log what would happen without bumping (used during rollout) |
| `cache_watcher_debug` | `false` | Log the fingerprint comparison when nothing changed (debug level) |
| `cache_watcher_interval_seconds` | `60` | Check frequency; beat still fires every minute, the task self-throttles via `cache_watcher.last_run` in the cache |

If the fingerprint query fails, or the cache backend is not Redis-like (tests use a local cache), the watcher does nothing rather than bumping on bad data.

### Rules for future code

- All cache reads and writes go through `shared/cache_lock`; entries are always stored as `(generation, value)` with the current generation.
- Never call `cache.set` or `cache.clear` for page content directly.
- To invalidate, call `bump_generation()` (or enqueue `clear_cache` if warming is wanted). Never delete entries to invalidate.
- New cache users don't need their own invalidation wiring — the watcher covers any DB change; only wire an immediate path if seconds matter.

### Debugging

- `redis-cli -n 1 --scan --pattern '*'` — list cache entries (keys look like `:1:index.`, `:1:event.<id>.<filter>`, plus `cache_generation` and the watcher's state keys).
- `redis-cli -n 1 GET cache_generation` — the current generation.
- Logs: `{app="racedb"}` in Loki, search for `cache watcher` (watcher decisions), `Bumping cache generation` and `warm_cache` (invalidation runs).
