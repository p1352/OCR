from io import BytesIO

from django.conf import settings
from PIL import Image
from rest_framework import serializers

from clients.models import Client

from .models import (
    Conversion,
    ExtractedTable,
    ExtractedText,
    QualityCheck,
    SourceImage,
)


class SourceImageSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )
    client_name = serializers.CharField(
        source="client.name", read_only=True, default=None
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SourceImage
        fields = [
            "id", "file_url", "original_name", "mime_type", "size_bytes",
            "width", "height", "client", "client_name", "status",
            "uploaded_by", "uploaded_by_name", "created_at",
        ]
        read_only_fields = [
            "id", "mime_type", "size_bytes", "width", "height",
            "status", "uploaded_by", "created_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class ImageUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False, allow_null=True
    )

    def validate_file(self, f):
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if f.size > max_bytes:
            raise serializers.ValidationError(
                f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo)."
            )
        # Ne jamais faire confiance au type MIME fourni par le navigateur :
        # on vérifie la signature réelle du fichier avec Pillow.
        try:
            pos = f.tell()
            img = Image.open(BytesIO(f.read()))
            img.verify()
            f.seek(pos)
            img = Image.open(f)
            detected = Image.MIME.get(img.format)
            f.seek(0)
        except Exception:
            f.seek(0)
            raise serializers.ValidationError(
                "Le fichier n'est pas une image valide ou est corrompu."
            )
        if detected not in settings.ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                f"Format non pris en charge ({detected}). "
                f"Formats acceptés : {', '.join(settings.ALLOWED_IMAGE_TYPES)}."
            )
        self._detected_mime = detected
        self._width, self._height = img.size
        return f


class ExtractedTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedText
        fields = [
            "id", "raw_text", "corrected_text", "language",
            "validation_status", "created_at", "updated_at",
        ]


class ExtractedTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedTable
        fields = [
            "id", "raw_data", "corrected_data",
            "validation_status", "created_at", "updated_at",
        ]


class QualityCheckSerializer(serializers.ModelSerializer):
    decided_by_name = serializers.CharField(
        source="decided_by.username", read_only=True, default=None
    )

    class Meta:
        model = QualityCheck
        fields = [
            "id", "confidence_score", "alerts", "decision",
            "decision_comment", "decided_by", "decided_by_name",
            "decided_at", "created_at", "updated_at",
        ]
        read_only_fields = ["confidence_score", "alerts", "decided_by",
                            "decided_at", "created_at", "updated_at"]


class ConversionSerializer(serializers.ModelSerializer):
    extracted_text = ExtractedTextSerializer(read_only=True)
    extracted_table = ExtractedTableSerializer(read_only=True)
    quality_check = QualityCheckSerializer(read_only=True)
    image_detail = SourceImageSerializer(source="image", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = Conversion
        fields = [
            "id", "image", "image_detail", "conversion_type", "status",
            "error_message", "model_used", "duration_ms", "created_by",
            "created_by_name", "created_at", "finished_at",
            "extracted_text", "extracted_table", "quality_check",
        ]
        read_only_fields = [
            "id", "status", "error_message", "model_used", "duration_ms",
            "created_by", "created_at", "finished_at",
        ]


class DecideSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["validated", "rejected"])
    comment = serializers.CharField(required=False, allow_blank=True, default="")
