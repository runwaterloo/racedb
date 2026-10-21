from django.core.management.base import BaseCommand

from racedbapp.tasks import clear_cache


class Command(BaseCommand):
    help = "Invalidate all generation-stamped cache entries and warm hot pages"

    def handle(self, *args, **options):
        clear_cache()
