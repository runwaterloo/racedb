# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-14 00:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0034_auto_20170304_2113'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endurathlete',
            name='division',
            field=models.CharField(choices=[('Ultimate', 'Ultimate'), ('Sport', 'Sport')], max_length=32),
        ),
        migrations.AlterField(
            model_name='endurathlete',
            name='gender',
            field=models.CharField(choices=[('F', 'Female'), ('M', 'Male')], max_length=1),
        ),
    ]
