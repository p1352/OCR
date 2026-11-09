from django.contrib import admin

from .models import (
    Conversion,
    ExtractedTable,
    ExtractedText,
    QualityCheck,
    SourceImage,
)


@admin.register(SourceImage)
class SourceImageAdmin(admin.ModelAdmin):
    list_display = ("original_name", "mime_type", "size_bytes", "client",
                    "status", "uploaded_by", "created_at")
    list_filter = ("status", "mime_type")
    search_fields = ("original_name",)


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "conversion_type", "status",
                    "duration_ms", "created_by", "created_at")
    list_filter = ("conversion_type", "status")


@admin.register(ExtractedText)
class ExtractedTextAdmin(admin.ModelAdmin):
    list_display = ("conversion", "language", "validation_status")


@admin.register(ExtractedTable)
class ExtractedTableAdmin(admin.ModelAdmin):
    list_display = ("conversion", "validation_status")


@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = ("conversion", "confidence_score", "decision",
                    "decided_by", "decided_at")
