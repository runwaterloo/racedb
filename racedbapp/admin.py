from django.contrib import admin

from .models import *


class ConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "value")
    search_fields = ("name", "value")
    ordering = ("name",)


admin.site.register(Config, ConfigAdmin)


class DistanceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "km", "showrecord")


admin.site.register(Distance, DistanceAdmin)

admin.site.register(Race)


class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "race", "distance", "city", "flickrsetid")
    search_fields = ("date", "race__name", "distance__name")
    ordering = ("-date",)


admin.site.register(Event, EventAdmin)


class ResultAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "place",
        "bib",
        "athlete",
        "gender",
        "category",
        "city",
        "chiptime",
        "guntime",
    )


admin.site.register(Result, ResultAdmin)


class RwmembertagAdmin(admin.ModelAdmin):
    list_display = ("name", "auto_select")
    ordering = ("-id",)


admin.site.register(Rwmembertag, RwmembertagAdmin)


class RwmemberAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    list_display = (
        "id",
        "name",
        "gender",
        "city",
        "joindate",
        "active",
        "member_tags",
        "photourl",
    )
    search_fields = ("name",)
    ordering = ("-id",)
    list_max_show_all = 5000
    readonly_fields = ("hasphotos",)

    def member_tags(self, obj):
        return " ".join([t.name for t in obj.tags.all()])


admin.site.register(Rwmember, RwmemberAdmin)


class RwmembercorrectionAdmin(admin.ModelAdmin):
    list_display = ("rwmember", "correction_type", "event", "place")
    search_fields = ("rwmember",)
    ordering = ("rwmember__id",)


admin.site.register(Rwmembercorrection, RwmembercorrectionAdmin)


class EndurathleteAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "division",
        "name",
        "gender",
        "age",
        "city",
        "province",
        "country",
    )
    list_filter = ("division", "gender", "country", "year")
    search_fields = ("name", "country")
    ordering = (
        "-year",
        "-division",
        "id",
    )


admin.site.register(Endurathlete, EndurathleteAdmin)


class EndurteamAdmin(admin.ModelAdmin):
    list_display = ("year", "name", "gender", "ismasters")
    list_filter = ("year",)
    search_fields = ("name",)
    ordering = ("-year", "name")
    readonly_fields = (
        "year",
        "name",
        "gender",
        "ismasters",
        "st1",
        "st2",
        "st3",
        "st4",
        "st5",
        "st6",
        "st7",
    )


admin.site.register(Endurteam, EndurteamAdmin)


class BowAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "year", "events")
    ordering = ("id",)


admin.site.register(Bow, BowAdmin)


class BowathleteAdmin(admin.ModelAdmin):
    list_display = ("bow", "category", "name", "gender")
    list_filter = ("bow",)
    ordering = ("bow__id", "id")


admin.site.register(Bowathlete, BowathleteAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "ismasters")
    ordering = ("name",)


admin.site.register(Category, CategoryAdmin)


class DurelayAdmin(admin.ModelAdmin):
    list_display = ("year", "team_place", "team_name", "team_time")
    ordering = ("-year", "team_place")


admin.site.register(Durelay, DurelayAdmin)


class RelayAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "place",
        "relay_team",
        "relay_team_place",
        "relay_team_time",
        "relay_leg",
    )


admin.site.register(Relay, RelayAdmin)


class SeriesAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "name",
        "slug",
        "event_ids",
        "show_records",
    )


admin.site.register(Series, SeriesAdmin)


class TimerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "website_url",
        "image_url",
    )


admin.site.register(Timer, TimerAdmin)


class TeamcategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
    )


admin.site.register(Teamcategory, TeamcategoryAdmin)
