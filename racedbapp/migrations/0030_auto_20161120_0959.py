# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-20 14:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0029_rwmember_city'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rwmembercorrection',
            name='bib',
        ),
        migrations.AddField(
            model_name='rwmembercorrection',
            name='place',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
