# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-17 00:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0020_samerace'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='event',
            options={},
        ),
        migrations.RemoveField(
            model_name='race',
            name='blurb',
        ),
        migrations.AddField(
            model_name='event',
            name='city',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
    ]
