from django.apps import AppConfig


class RacedbappConfig(AppConfig):
    name = "racedbapp"
    verbose_name = "Racedb Application"

    def ready(self):
        import racedbapp.signals
