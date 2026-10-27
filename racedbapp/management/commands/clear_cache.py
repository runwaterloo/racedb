from django.core.management.base import BaseCommand

from racedbapp.tasks import clear_cache


class Command(BaseCommand):
    help = "Clear the cache and warm hot pages"

    def handle(self, *args, **options):
        clear_cache(source="command")
