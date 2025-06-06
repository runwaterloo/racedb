from rest_framework import serializers

from ...models import Distance, Race, Result


class V1DistanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distance
        fields = [
            "id",
            "slug",
            "name",
            "km",
            "showrecord",
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
