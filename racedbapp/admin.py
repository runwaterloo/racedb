from django.contrib import admin

from .models import (
    Bow,
    Bowathlete,
    Category,
    Config,
    Distance,
    Durelay,
    Endurathlete,
    Endurteam,
    Event,
    Race,
    Relay,
    Result,
    Rwmember,
    Rwmembercorrection,
    Rwmembertag,
    Sequel,
    Series,
    Teamcategory,
    Timer,
)


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "value")
    search_fields = ("name", "value")
    ordering = ("name",)


@admin.register(Distance)
class DistanceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "km", "showrecord")


admin.site.register(Race)


def delete_all_results_for_event(modeladmin, request, queryset):
    from .models import Result

    event_ids = queryset.values_list("id", flat=True).distinct()
    count = 0
    for event_id in event_ids:
        deleted, _ = Result.objects.filter(event_id=event_id).delete()
        count += deleted
    modeladmin.message_user(request, f"Deleted {count} results for selected events.")


delete_all_results_for_event.short_description = "Delete all results for selected events"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "race", "distance", "city", "flickrsetid")
    search_fields = ("date", "race__name", "distance__name")
    ordering = ("-date",)
    actions = [delete_all_results_for_event]


@admin.register(Result)
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


@admin.register(Rwmembertag)
class RwmembertagAdmin(admin.ModelAdmin):
    list_display = ("name", "auto_select")
    ordering = ("-id",)


@admin.register(Rwmember)
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


@admin.register(Rwmembercorrection)
class RwmembercorrectionAdmin(admin.ModelAdmin):
    list_display = ("rwmember", "correction_type", "event", "place")
    search_fields = ("rwmember",)
    ordering = ("rwmember__id",)


@admin.register(Endurathlete)
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


@admin.register(Endurteam)
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


@admin.register(Bow)
class BowAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "year", "events")
    ordering = ("id",)


@admin.register(Bowathlete)
class BowathleteAdmin(admin.ModelAdmin):
    list_display = ("bow", "category", "name", "gender")
    list_filter = ("bow",)
    ordering = ("bow__id", "id")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "ismasters")
    ordering = ("name",)


@admin.register(Durelay)
class DurelayAdmin(admin.ModelAdmin):
    list_display = ("year", "team_place", "team_name", "team_time")
    ordering = ("-year", "team_place")


@admin.register(Relay)
class RelayAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "place",
        "relay_team",
        "relay_team_place",
        "relay_team_time",
        "relay_leg",
    )


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "name",
        "slug",
        "event_ids",
        "show_records",
    )


@admin.register(Timer)
class TimerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "website_url",
        "image_url",
    )


@admin.register(Teamcategory)
class TeamcategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
    )


@admin.register(Sequel)
class SequelAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
