# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-02-12 16:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0004_race_blurb'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamresult',
            name='estimated',
            field=models.BooleanField(default=False),
        ),
    ]
