# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-05 02:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0033_event_flickrsetid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='flickrsetid',
            field=models.BigIntegerField(blank=True, default=None, null=True),
        ),
    ]
