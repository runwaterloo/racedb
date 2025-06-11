from rest_framework import serializers

from ...models import Category, Distance, Event, Race, Result, Rwmember, Series


class V1CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "ismasters",
        ]


class V1DistanceSerializer(serializers.ModelSerializer):
    results_url = serializers.SerializerMethodField()

    class Meta:
        model = Distance
        fields = [
            "id",
            "slug",
            "name",
            "km",
            "showrecord",
            "results_url",
        ]

    def get_results_url(self, obj):
        request = self.context.get("request")
        url = f"/v1/distances/{obj.id}/results/"
        if request:
            return request.build_absolute_uri(url)
        return url


class V1EventSerializer(serializers.ModelSerializer):
    race_name = serializers.CharField(source="race.name", read_only=True)
    race_shortname = serializers.CharField(source="race.shortname", read_only=True)
    race_slug = serializers.CharField(source="race.slug", read_only=True)
    distance_km = serializers.CharField(source="distance.km", read_only=True)
    distance_name = serializers.CharField(source="distance.name", read_only=True)
    distance_slug = serializers.CharField(source="distance.slug", read_only=True)
    results_exist = serializers.BooleanField(read_only=True)
    results_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "date",
            "race",
            "race_name",
            "race_shortname",
            "race_slug",
            "distance",
            "distance_km",
            "distance_name",
            "distance_slug",
            "city",
            "flickrsetid",
            "youtube_id",
            "youtube_offset_seconds",
            "youtube_duration_seconds",
            "medals",
            "timer",
            "results_exist",
            "results_url",
        ]

    def get_results_url(self, obj):
        request = self.context.get("request")
        url = f"/v1/events/{obj.id}/results/"
        if request:
            return request.build_absolute_uri(url)
        return url


class V1RwmemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rwmember
        fields = [
            "id",
            "name",
            "slug",
            "gender",
            "year_of_birth",
            "city",
            "joindate",
            "photourl",
            "altname",
            "hasphotos",
            "tags",
        ]


class V1RaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Race
        fields = [
            "id",
            "name",
            "shortname",
            "slug",
        ]


class V1ResultSerializer(serializers.ModelSerializer):
    rwmember_slug = serializers.CharField(source="rwmember.slug", read_only=True, allow_null=True)
    category_ismasters = serializers.BooleanField(source="category.ismasters", read_only=True)

    class Meta:
        model = Result
        fields = [
            "id",
            "event",
            "place",
            "bib",
            "athlete",
            "rwmember",
            "rwmember_slug",
            "gender",
            "gender_place",
            "category",
            "category_place",
            "category_ismasters",
            "age",
            "chiptime",
            "guntime",
            "city",
            "province",
            "country",
            "division",
            "isrwpb",
        ]


class V1SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = [
            "id",
            "year",
            "name",
            "slug",
            "event_ids",
            "show_records",
        ]
