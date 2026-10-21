from django.core.management.base import BaseCommand

from racedbapp.tasks import clear_cache


class Command(BaseCommand):
    help = "Deprecated: use bump_cache_generation (cache.clear() was replaced by generation bumps, #387)"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("clear_cache is deprecated; use bump_cache_generation")
        )
        clear_cache()
