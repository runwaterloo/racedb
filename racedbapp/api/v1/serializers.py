from rest_framework import serializers

from ...models import Category, Distance, Race, Result, Series


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
    class Meta:
        model = Result
        fields = [
            "id",
            "event",
            "place",
            "bib",
            "athlete",
            "rwmember",
            "gender",
            "gender_place",
            "category",
            "category_place",
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
