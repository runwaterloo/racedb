# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-05-24 01:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0039_auto_20170422_2138'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bowathlete',
            name='gender',
            field=models.CharField(choices=[('F', 'Female'), ('M', 'Male')], max_length=1),
        ),
    ]
