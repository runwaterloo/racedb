# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-01 21:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0049_auto_20171129_1904'),
    ]

    operations = [
        migrations.RenameField(
            model_name='result',
            old_name='catergory_place',
            new_name='category_place',
        ),
    ]
