from django.contrib import admin

from .models import *

class ConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')
    search_fields = ('name', 'value')
    ordering = ('name',)
admin.site.register(Config, ConfigAdmin)

class DistanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'km', 'showrecord')
admin.site.register(Distance, DistanceAdmin)

admin.site.register(Race)

class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'race', 'distance', 'city', 'flickrsetid')
    search_fields = ('date', 'race__name', 'distance__name')
    ordering = ('-date',)
    readonly_fields = ('race', 'distance', 'date', 'city', 'resultsurl')
admin.site.register(Event, EventAdmin)

class ResultAdmin(admin.ModelAdmin):
    list_display = ('event', 'place', 'bib', 'athlete', 'gender', 'category', 'city', 'chiptime', 'guntime')
admin.site.register(Result, ResultAdmin)

admin.site.register(Rwmembertag)

class RwmemberAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    list_display = ('id', 'name', 'gender', 'city', 'joindate', 'active', 'photourl')
    search_fields = ('name',)
    ordering = ('name',)
    list_max_show_all = 1000
    readonly_fields = ('hasphotos',)
admin.site.register(Rwmember, RwmemberAdmin)

class RwmembercorrectionAdmin(admin.ModelAdmin):
    list_display = ('rwmember', 'correction_type', 'event', 'place')
    search_fields = ('rwmember',)
    ordering = ('rwmember__id',)
admin.site.register(Rwmembercorrection, RwmembercorrectionAdmin)

class EndurathleteAdmin(admin.ModelAdmin):
    list_display = ('year', 'division', 'name', 'gender', 'age',
                    'city', 'province', 'country')
    list_filter = ('division', 'gender', 'country', 'year')
    search_fields = ('name', 'country')
    ordering = ('-year', '-division', 'id',)
admin.site.register(Endurathlete, EndurathleteAdmin)

class BowAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'year', 'events')
    ordering = ('id',)
admin.site.register(Bow, BowAdmin) 

class BowathleteAdmin(admin.ModelAdmin):
    list_display = ('bow', 'category', 'name', 'gender')
    list_filter = ('bow',)
    ordering = ('bow__id', 'id')
admin.site.register(Bowathlete, BowathleteAdmin) 

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'ismasters')
    ordering = ('name',)
admin.site.register(Category, CategoryAdmin) 
