from collections import namedtuple
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count, Min, Q, Sum

import racedbapp.shared.utils as utils

#########################################
# Query Sets                            #
#########################################
namedtresult = namedtuple(
    "nt", ["event", "team_category", "top", "winning_team", "total_time", "avg_time"]
)
namediresult = namedtuple(
    "ni",
    [
        "place",
        "female_athlete",
        "female_time",
        "female_member_slug",
        "female_result",
        "male_athlete",
        "male_time",
        "male_member_slug",
        "male_result",
    ],
)


class ResultQuerySet(models.QuerySet):
    def hasmasters(self, event):
        if self.filter(event=event, category__ismasters=True).first() is None:
            if self.filter(event=event, age__gte=40).first() is None:
                return False
            else:
                return True
        else:
            return True

    def hasage(self, event):
        if self.filter(event=event, age__gte=1).first() is None:
            return False
        else:
            return True

    def topmasters(self, event):
        topfemale = (
            self.filter(event=event, gender="F")
            .filter(Q(category__ismasters=True) | Q(age__gte=40))
            .first()
        )
        topmale = (
            self.filter(event=event, gender="M")
            .filter(Q(category__ismasters=True) | Q(age__gte=40))
            .first()
        )
        if topfemale:
            femaletime = topfemale.guntime
            female_member_slug = None
            female_member = topfemale.rwmember
            if female_member:
                female_member_slug = female_member.slug
            topfemale_athlete = topfemale.athlete
        else:
            topfemale_athlete = femaletime = female_member_slug = None
        if topmale:
            maletime = topmale.guntime
            male_member_slug = None
            male_member = topmale.rwmember
            if male_member:
                male_member_slug = male_member.slug
            topmale_athlete = topmale.athlete
        else:
            topmale_athlete = maletime = male_member_slug = None
        return namediresult(
            "1st Master",
            topfemale_athlete,
            femaletime,
            female_member_slug,
            topfemale,
            topmale_athlete,
            maletime,
            male_member_slug,
            topmale,
        )


class EndurraceresultQuerySet(models.QuerySet):
    def hasmasters(self, year):
        if self.filter(year=year, category__ismasters=True).first() is None:
            return False
        else:
            return True

    def topmasters(self, year):
        topfemale = self.filter(year=year, category__ismasters=True, gender="F").order_by(
            "guntime"
        )[0]
        topmale = self.filter(year=year, category__ismasters=True, gender="M").order_by("guntime")[
            0
        ]
        femaletime = utils.truncate_time(topfemale.guntime)
        maletime = utils.truncate_time(topmale.guntime)
        return namediresult(
            "1st Master",
            topfemale.athlete,
            femaletime,
            None,
            topfemale,
            topmale.athlete,
            maletime,
            None,
            topmale,
        )


class TeamcategoryQuerySet(models.QuerySet):
    def of_results(self, results):
        return self.filter(pk__in=results.values("team_category").distinct())


class TeamresultQuerySet(models.QuerySet):
    def winning_team_details(self, team_category):
        return self.filter(team_category=team_category, team_place=1, counts=True).aggregate(
            top=Count("athlete_time"),
            total=Sum("athlete_time"),
            avg=Avg("athlete_time"),
            team_name=Min("team_name"),
        )

    def of_event(self, event):
        results = self.filter(event=event, counts=True)
        for team_category in Teamcategory.objects.of_results(results):
            winner = results.winning_team_details(team_category)
            total_time = utils.truncate_time(winner["total"])
            avg_time = utils.truncate_time(winner["avg"])
            yield namedtresult(
                event,
                team_category,
                winner["top"],
                winner["team_name"].strip(),
                total_time,
                avg_time,
            )


#########################################


class Config(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return "name={}, value={}".format(self.name, self.value)


class Distance(models.Model):
    prename = models.CharField(max_length=25)
    name = models.CharField(max_length=25, unique=True)
    slug = models.SlugField(unique=True)
    km = models.DecimalField(max_digits=9, decimal_places=5)
    showrecord = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Race(models.Model):
    name = models.CharField(max_length=50, unique=True)
    shortname = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Samerace(models.Model):
    old_race = models.ForeignKey(Race, related_name="old_race", on_delete=models.CASCADE)
    current_race = models.ForeignKey(Race, related_name="current_race", on_delete=models.CASCADE)


class Category(models.Model):
    name = models.CharField(max_length=20, unique=True)
    ismasters = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Teamcategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    objects = TeamcategoryQuerySet.as_manager()
    sortorder = models.IntegerField()

    class Meta:
        ordering = ("sortorder",)

    def __str__(self):
        return self.name


class Timer(models.Model):
    name = models.CharField(max_length=100)
    website_url = models.URLField(max_length=500)
    image_url = models.URLField(max_length=500)

    def __str__(self):
        return self.name


class Event(models.Model):
    MEDALS_CHOICES = (("none", "none"), ("standard", "standard"), ("classic-5oa", "classic-5oa"))
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    distance = models.ForeignKey(Distance, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    city = models.CharField(max_length=50)
    resultsurl = models.URLField(max_length=500, null=True, blank=True)
    flickrsetid = models.BigIntegerField(default=None, null=True, blank=True)
    youtube_id = models.CharField(
        max_length=50, blank=True, help_text="Just the video id, not the whole URL"
    )
    youtube_offset_seconds = models.IntegerField(
        default=None,
        null=True,
        blank=True,
        help_text="Elapsed race time (in seconds) at start of video",
    )
    youtube_duration_seconds = models.IntegerField(
        default=None,
        null=True,
        blank=True,
        help_text=(
            "OPTIONAL: Total duration (in seconds) of YouTube video. This is "
            "only required if the video cuts off early."
        ),
    )
    medals = models.CharField(max_length=32, choices=MEDALS_CHOICES, default="none")
    timer = models.ForeignKey(Timer, models.SET_NULL, null=True, blank=True, default=None)
    sequel = models.ForeignKey(
        "Sequel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        help_text="Optional: Attach a Sequel instance to this event.",
    )
    custom_logo_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Override default race logo with a custom one for this event",
    )

    class Meta:
        unique_together = ("race", "distance", "date", "sequel")

    def clean(self):
        # Enforce uniqueness for (race, distance, year, sequel)
        query = Event.objects.filter(
            race=self.race,
            distance=self.distance,
            date__year=self.date.year,
            sequel=self.sequel,
        )
        if self.pk:
            query = query.exclude(pk=self.pk)
        if query.exists():
            raise ValidationError(
                {"__all__": "An event with this race, distance, year, and sequel already exists."}
            )

    def __str__(self):
        return "{} {} {}".format(self.date.year, self.race, self.distance)


class Rwmembertag(models.Model):
    name = models.CharField(max_length=32)
    auto_select = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Rwmember(models.Model):
    GENDER_CHOICES = (("F", "Female"), ("M", "Male"), ("NB", "Nonbinary"))

    def membertag_defaults():
        return Rwmembertag.objects.filter(auto_select=True)

    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True, help_text="https://blog.tersmitten.nl/slugify/")
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, blank=True)
    year_of_birth = models.IntegerField(null=True, blank=True)
    city = models.CharField(max_length=50)
    joindate = models.DateField(default=datetime.now)
    photourl = models.URLField(max_length=500, null=True, blank=True)
    altname = models.CharField(max_length=64, blank=True, help_text="Optional, e.g. maiden name")
    active = models.BooleanField(default=True, db_index=True)
    tags = models.ManyToManyField(Rwmembertag, blank=True, default=membertag_defaults)
    hasphotos = models.BooleanField(default=False, help_text="Automatically set by system")

    def __str__(self):
        return self.name


class Result(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    athlete = models.CharField(max_length=100)
    gender = models.CharField(max_length=2)
    city = models.CharField(max_length=50)
    place = models.IntegerField()
    bib = models.CharField(max_length=6, blank=True)
    chiptime = models.DurationField(null=True)
    guntime = models.DurationField(null=True)
    age = models.IntegerField(null=True)
    division = models.CharField(max_length=32, blank=True)
    province = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    rwmember = models.ForeignKey(Rwmember, null=True, default=None, on_delete=models.CASCADE)
    gender_place = models.IntegerField(null=True, blank=True)
    category_place = models.IntegerField(null=True, blank=True)
    isrwpb = models.BooleanField(default=False, blank=True)
    objects = ResultQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["rwmember", "event"]),
        ]
        ordering = ("place",)
        unique_together = ("event", "place")

    def __str__(self):
        return str((self.event, self.bib))


class Wheelchairresult(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    athlete = models.CharField(max_length=100)
    gender = models.CharField(max_length=2)
    city = models.CharField(max_length=50)
    place = models.IntegerField()
    bib = models.CharField(max_length=6, blank=True)
    chiptime = models.DurationField(null=True)
    guntime = models.DurationField(null=True)
    objects = ResultQuerySet.as_manager()

    def __str__(self):
        return str((self.event, self.bib))


class Teamresult(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    team_category = models.ForeignKey(Teamcategory, on_delete=models.CASCADE)
    team_place = models.IntegerField()
    team_name = models.CharField(max_length=64)
    athlete_team_place = models.IntegerField()
    athlete_time = models.DurationField()
    athlete_name = models.CharField(max_length=64)
    counts = models.BooleanField()
    estimated = models.BooleanField(default=False)
    objects = TeamresultQuerySet.as_manager()

    class Meta:
        unique_together = ("event", "team_category", "team_name", "athlete_team_place")
        ordering = ("event", "team_category", "team_place", "athlete_team_place")

    def __str__(self):
        return str((self.event, self.team_name, self.athlete_name))


class Endurraceresult(models.Model):
    year = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    athlete = models.CharField(max_length=100)
    gender = models.CharField(max_length=2)
    city = models.CharField(max_length=50)
    bib = models.CharField(max_length=6, blank=True)
    guntime = models.DurationField()
    fivektime = models.DurationField()
    eightktime = models.DurationField()
    objects = EndurraceresultQuerySet.as_manager()

    class Meta:
        unique_together = ("year", "athlete")


class Bow(models.Model):
    name = models.CharField(max_length=16, unique=True)
    slug = models.SlugField(unique=True)
    year = models.IntegerField()
    events = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class Bowathlete(models.Model):
    GENDER_CHOICES = (("F", "Female"), ("M", "Male"), ("NB", "Nonbinary"))
    bow = models.ForeignKey(Bow, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("bow", "name")


class Prime(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    place = models.IntegerField()
    gender = models.CharField(max_length=2)
    time = models.DurationField(null=True)


class Relay(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    place = models.IntegerField(
        help_text="Overall place this person finished in the individual event"
    )
    relay_team = models.CharField(max_length=128, help_text="Relay team name")
    relay_team_place = models.IntegerField(help_text="Place the relay team finished")
    relay_team_time = models.DurationField(null=True, help_text="Total time for the relay team")
    relay_leg = models.IntegerField(help_text="Relay leg for this individual (e.g. 1, 2)")


class Split(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    place = models.IntegerField()
    split_num = models.IntegerField()
    split_time = models.DurationField(null=True)

    class Meta:
        unique_together = ("event", "place", "split_num")


class Endurathlete(models.Model):
    DIVISION_CHOICES = (("Ultimate", "Ultimate"), ("Sport", "Sport"))
    GENDER_CHOICES = (("F", "Female"), ("M", "Male"), ("NB", "Nonbinary"))
    year = models.IntegerField()
    division = models.CharField(max_length=32, choices=DIVISION_CHOICES)
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES)
    age = models.IntegerField(null=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        unique_together = ("year", "division", "name")


class Endurteam(models.Model):
    year = models.IntegerField(
        help_text=(
            "Teams should not be added or modified in the admin, only deleted "
            "if necessary. They get created and updated automatically from results."
        )
    )
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=2)
    ismasters = models.BooleanField(default=False)
    st1 = models.CharField(max_length=100)
    st2 = models.CharField(max_length=100)
    st3 = models.CharField(max_length=100)
    st4 = models.CharField(max_length=100)
    st5 = models.CharField(max_length=100)
    st6 = models.CharField(max_length=100)
    st7 = models.CharField(max_length=100)

    class Meta:
        unique_together = ("year", "name")


class Rwmembercorrection(models.Model):
    CORRECTION_TYPE_CHOICES = (("exclude", "exclude"), ("include", "include"))
    rwmember = models.ForeignKey(Rwmember, on_delete=models.CASCADE)
    correction_type = models.CharField(max_length=7, choices=CORRECTION_TYPE_CHOICES)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    place = models.IntegerField()


class Phototag(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    tag = models.CharField(max_length=64)


class Durelay(models.Model):
    year = models.IntegerField()
    team_place = models.IntegerField()
    team_name = models.CharField(max_length=128)
    team_time = models.DurationField(null=True)
    run1_athlete = models.CharField(max_length=128)
    run1_time = models.DurationField(null=True)
    bike_athlete = models.CharField(max_length=128)
    bike_time = models.DurationField(null=True)
    run2_athlete = models.CharField(max_length=128)
    run2_time = models.DurationField(null=True)


class Series(models.Model):
    year = models.IntegerField()
    name = models.CharField(max_length=256)
    slug = models.SlugField()
    event_ids = models.CharField(max_length=64, help_text="Comma-separated list of event IDs")
    show_records = models.BooleanField(default=True)

    class Meta:
        unique_together = ("year", "slug")
        verbose_name_plural = "Series"


class Sequel(models.Model):
    name = models.CharField(max_length=256)
    slug = models.SlugField(unique=True)

    def clean(self):
        if self.slug == "team":
            raise ValidationError({"slug": "'team' is not allowed as a slug value."})

    def __str__(self):
        return self.name
