# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-11 19:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0044_delete_phototagbackup'),
    ]

    operations = [
        migrations.AddField(
            model_name='rwmember',
            name='year_of_birth',
            field=models.IntegerField(null=True),
        ),
    ]
