# Test renovate configuration locally

```bash
docker run --rm \
  --user $(id -u):$(id -g) \
  -e RENOVATE_DRY_RUN=full \
  -e RENOVATE_PLATFORM=local \
  -e LOG_LEVEL=debug \
  -e RENOVATE_CONFIG_FILE=.github/renovate.json \
  -v "$(pwd)":/mnt/renovate \
  -w /mnt/renovate \
  renovate/renovate
```
