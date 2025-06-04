from rest_framework import serializers

from ...models import Result


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
