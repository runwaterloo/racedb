# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-15 03:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0028_auto_20161113_1557'),
    ]

    operations = [
        migrations.AddField(
            model_name='rwmember',
            name='city',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
    ]
