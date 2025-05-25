#!/usr/bin/env python
from django.core.management.base import BaseCommand

from racedbapp.tasks import clear_cache


class Command(BaseCommand):
    def handle(self, *args, **options):
        clear_cache()
