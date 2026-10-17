from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("racedbapp", "0080_remove_distance_prename"),
    ]

    operations = [
        migrations.AddField(
            model_name="teamcategory",
            name="counts",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Number of individual results that count toward the team result. "
                    "If null, use the counts column on the results sheet."
                ),
                null=True,
            ),
        ),
    ]
