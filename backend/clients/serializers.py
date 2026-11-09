from rest_framework import serializers

from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    image_count = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = Client
        fields = [
            "id", "name", "email", "phone", "address", "notes",
            "status", "image_count", "created_by", "created_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]
