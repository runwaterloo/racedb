# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-12 00:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0009_auto_20160404_0954'),
    ]

    operations = [
        migrations.CreateModel(
            name='Prime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DurationField(null=True)),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='racedbapp.Result')),
            ],
        ),
    ]
