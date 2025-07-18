# Generated by Django 4.0.3 on 2022-04-04 22:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("racedbapp", "0065_auto_20200206_2310"),
    ]

    operations = [
        migrations.CreateModel(
            name="Series",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("year", models.IntegerField()),
                ("name", models.CharField(max_length=256)),
                ("slug", models.SlugField()),
                (
                    "event_ids",
                    models.CharField(
                        help_text="Comma-separated list of event IDs", max_length=64
                    ),
                ),
                ("show_records", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "Series",
                "unique_together": {("year", "slug")},
            },
        ),
    ]
