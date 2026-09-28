"""Serializers for question query parameters."""

from rest_framework import serializers


class QuestionQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=100)
    type = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=("1", "2", "3", "4"),
    )
    point = serializers.CharField(required=False, allow_blank=True, max_length=200)
    points = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    point_status = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=("linked", "unlinked"),
    )
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
