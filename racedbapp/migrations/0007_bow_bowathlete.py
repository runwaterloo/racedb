# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-03-17 16:21
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('racedbapp', '0006_auto_20160215_1942'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('year', models.IntegerField()),
                ('events', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='Bowathlete',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('gender', models.CharField(max_length=1)),
                ('bow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='racedbapp.Bow')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='racedbapp.Category')),
            ],
        ),
    ]
