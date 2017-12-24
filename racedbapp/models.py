from django.db import models
from django.db.models import Avg, Count, Min, Sum, Q
from collections import namedtuple
from datetime import datetime
from . import utils

#########################################
# Query Sets                            #
#########################################
namedtresult = namedtuple('nt', ['event', 'team_category', 'top', 'winning_team',
                                 'total_time', 'avg_time'])
namediresult = namedtuple('ni', ['place', 'female_athlete', 'female_time', 'female_member_slug',
                                 'male_athlete', 'male_time', 'male_member_slug'])
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
        topfemale = self.filter(event=event, gender='F').filter(Q(category__ismasters=True) | Q(age__gte=40))[0]
        topmale = self.filter(event=event, gender='M').filter(Q(category__ismasters=True) | Q(age__gte=40))[0]
        femaletime = utils.truncate_time(topfemale.guntime)
        female_member_slug = None
        female_member = topfemale.rwmember
        if female_member:
            female_member_slug = female_member.slug
        maletime = utils.truncate_time(topmale.guntime)
        male_member_slug = None
        male_member = topmale.rwmember
        if male_member:
            male_member_slug = male_member.slug
        return namediresult('1st Master', topfemale.athlete, femaletime, female_member_slug,
                            topmale.athlete, maletime, male_member_slug)

class EndurraceresultQuerySet(models.QuerySet):
    def hasmasters(self, year):
        if self.filter(year=year, category__ismasters=True).first() is None:
            return False
        else:
            return True
    def topmasters(self, year):
        topfemale = self.filter(year=year, category__ismasters=True,gender='F').order_by('guntime')[0]
        topmale = self.filter(year=year, category__ismasters=True,gender='M').order_by('guntime')[0]
        femaletime = utils.truncate_time(topfemale.guntime)
        maletime = utils.truncate_time(topmale.guntime)
        return namediresult('1st Master', topfemale.athlete, femaletime, None, topmale.athlete, maletime, None)
        

class TeamcategoryQuerySet(models.QuerySet):
    def of_results(self, results):
        return self.filter(pk__in=results.values('team_category').distinct())


class TeamresultQuerySet(models.QuerySet):
    def winning_team_details(self, team_category):
        return (self
                .filter(
                    team_category=team_category, team_place=1, counts=True)
                .aggregate(
                    top=Count('athlete_time'),
                    total=Sum('athlete_time'),
                    avg=Avg('athlete_time'),
                    team_name=Min('team_name')
                ))

    def of_event(self, event):
        results = self.filter(event=event, counts=True)
        for team_category in Teamcategory.objects.of_results(results):
            winner = results.winning_team_details(team_category)
            total_time = utils.truncate_time(winner['total'])
            avg_time = utils.truncate_time(winner['avg'])
            yield namedtresult(event, team_category, winner['top'], winner['team_name'].strip(),
                   total_time, avg_time)

#########################################

class Config(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=200)
    def __str__(self):
        return 'name={}, value={}'.format(self.name, self.value)

class Distance(models.Model):
    prename = models.CharField(max_length=25)
    name = models.CharField(max_length=25, unique=True)
    slug = models.SlugField(unique=True)
    km = models.DecimalField(max_digits=9, decimal_places=5)
    showrecord = models.BooleanField(default=False)
    def __str__(self): 
        return self.name

class Race(models.Model):
    prename = models.CharField(max_length=50)
    name = models.CharField(max_length=50, unique=True)
    shortname = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    def __str__(self): 
        return self.name

class Samerace(models.Model):                                                        
    old_race = models.ForeignKey(Race, related_name='old_race')                  
    current_race = models.ForeignKey(Race, related_name='current_race')          

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
        ordering = ('sortorder', )
    def __str__(self): 
        return self.name

class Event(models.Model):
    race = models.ForeignKey(Race)
    distance = models.ForeignKey(Distance)
    date = models.DateField(db_index=True)
    city = models.CharField(max_length=50)
    resultsurl = models.URLField(max_length=500, null=True, blank=True)
    flickrsetid = models.BigIntegerField(default=None, null=True, blank=True)
    youtube_id = models.CharField(max_length=50, blank=True, help_text='Just the video id, not the whole URL')
    youtube_offset_seconds = models.IntegerField(default=None, null=True, blank=True, help_text='Elapsed race time (in seconds) at start of video')
    class Meta:
        unique_together = ('race', 'distance', 'date')
    #    ordering = ('-date', '-distance__km')
    def __str__(self): 
        return '{} {} {}'.format(self.date.year, self.race, self.distance)

class Rwmembertag(models.Model):
    name = models.CharField(max_length=32)
    def __str__(self): 
        return self.name

class Rwmember(models.Model):
    GENDER_CHOICES = (('F', 'Female'),('M', 'Male'))
    def membertag_defaults():
        db_membertag_defaults = Config.objects.filter(name='membertag_default').values('value')
        return Rwmembertag.objects.filter(name__in=db_membertag_defaults)
    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True, help_text="https://blog.tersmitten.nl/slugify/")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    year_of_birth = models.IntegerField(null=True, blank=True)
    city = models.CharField(max_length=50)
    joindate = models.DateField(default=datetime.now)
    photourl = models.URLField(max_length=500, null=True, blank=True)
    altname = models.CharField(max_length=64, blank=True, help_text="Optional, e.g. maiden name")
    active = models.BooleanField(default=True)
    tags = models.ManyToManyField(Rwmembertag, blank=True, default=membertag_defaults)
    hasphotos = models.BooleanField(default=False, help_text="Automatically set by system")
    def __str__(self): 
        return self.name

class Result(models.Model):
    event = models.ForeignKey(Event)
    category = models.ForeignKey(Category)
    athlete = models.CharField(max_length=100)
    gender = models.CharField(max_length=1)
    city = models.CharField(max_length=50)
    place= models.IntegerField()
    bib = models.CharField(max_length=6, blank=True)
    chiptime = models.DurationField(null=True)
    guntime = models.DurationField(null=True)
    age = models.IntegerField(null=True)
    division = models.CharField(max_length=32, blank=True)
    province = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    rwmember = models.ForeignKey(Rwmember, null=True, default=None)
    gender_place = models.IntegerField(null=True, blank=True)
    category_place = models.IntegerField(null=True, blank=True)
    isrwpb = models.BooleanField(default=False, blank=True)
    objects = ResultQuerySet.as_manager()
    class Meta:
        unique_together = ('event', 'place')
        ordering = ('place', )
    def __str__(self): 
        return str((self.event, self.bib))

class Wheelchairresult(models.Model):
    event = models.ForeignKey(Event)
    category = models.ForeignKey(Category)
    athlete = models.CharField(max_length=100)
    gender = models.CharField(max_length=1)
    city = models.CharField(max_length=50)
    place= models.IntegerField()
    bib = models.CharField(max_length=6, blank=True)
    chiptime = models.DurationField(null=True)
    guntime = models.DurationField(null=True)
    objects = ResultQuerySet.as_manager()
    def __str__(self): 
        return str((self.event, self.bib))

class Teamresult(models.Model):
    event = models.ForeignKey(Event)
    team_category = models.ForeignKey(Teamcategory)
    team_place= models.IntegerField()
    team_name = models.CharField(max_length=64)
    athlete_team_place = models.IntegerField()
    athlete_time = models.DurationField()
    athlete_name = models.CharField(max_length=64)
    counts = models.BooleanField()
    estimated = models.BooleanField(default=False)
    objects = TeamresultQuerySet.as_manager()
    class Meta:
        unique_together = ('event', 'team_category', 'team_name', 'athlete_team_place')
        ordering = ('event', 'team_category', 'team_place', 'athlete_team_place')
    def __str__(self):
        return str((self.event, self.team_name, self.athlete_name))

class Endurraceresult(models.Model):
    year = models.IntegerField()
    category = models.ForeignKey(Category)
    athlete = models.CharField(max_length=100)
    gender = models.CharField(max_length=1)
    city = models.CharField(max_length=50)
    bib = models.CharField(max_length=6, blank=True)
    guntime = models.DurationField()
    fivektime = models.DurationField()
    eightktime = models.DurationField()
    objects = EndurraceresultQuerySet.as_manager()
    class Meta:
        unique_together = ('year', 'athlete')

class Bow(models.Model):
    name = models.CharField(max_length=16, unique=True)
    slug = models.SlugField(unique=True)
    year = models.IntegerField()
    events = models.CharField(max_length=32)
    def __str__(self):
        return self.name

class Bowathlete(models.Model):
    GENDER_CHOICES = (('F', 'Female'),('M', 'Male'))
    bow = models.ForeignKey(Bow)
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    category = models.ForeignKey(Category)
    class Meta:
        unique_together = ('bow', 'name')

class Prime(models.Model):
    event = models.ForeignKey(Event)
    place = models.IntegerField()
    gender = models.CharField(max_length=1)
    time = models.DurationField(null=True)

class Split(models.Model):
    event = models.ForeignKey(Event)
    place = models.IntegerField()
    split_num = models.IntegerField()
    split_time = models.DurationField(null=True)
    class Meta:
        unique_together = ('event', 'place', 'split_num')

class Endurathlete(models.Model):
    DIVISION_CHOICES = (('Ultimate', 'Ultimate'),('Sport', 'Sport'))
    GENDER_CHOICES = (('F', 'Female'),('M', 'Male'))
    year = models.IntegerField()
    division = models.CharField(max_length=32, choices=DIVISION_CHOICES)
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    age = models.IntegerField(null=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    class Meta:
        unique_together = ('year', 'division', 'name')

class Endurteam(models.Model):
    year = models.IntegerField()
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1)
    ismasters = models.BooleanField(default=False)
    st1 = models.CharField(max_length=100)
    st2 = models.CharField(max_length=100)
    st3 = models.CharField(max_length=100)
    st4 = models.CharField(max_length=100)
    st5 = models.CharField(max_length=100)
    st6 = models.CharField(max_length=100)
    st7 = models.CharField(max_length=100)
    class Meta:
        unique_together = ('year', 'name')

class Rwmembercorrection(models.Model):
    CORRECTION_TYPE_CHOICES = (('exclude', 'exclude'),('include', 'include'))
    rwmember = models.ForeignKey(Rwmember)
    correction_type = models.CharField(max_length=7, choices=CORRECTION_TYPE_CHOICES)
    event = models.ForeignKey(Event)
    place= models.IntegerField()

class Phototag(models.Model):
    event = models.ForeignKey(Event)
    tag = models.CharField(max_length=64)
