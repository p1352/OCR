import os
import uuid

from django.conf import settings
from django.db import models


def image_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"images/{uuid.uuid4().hex}{ext}"


class SourceImage(models.Model):
    """Image importée par un utilisateur."""

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        PROCESSING = "processing", "En cours"
        DONE = "done", "Terminée"
        FAILED = "failed", "Échouée"

    file = models.ImageField("fichier", upload_to=image_upload_path)
    original_name = models.CharField("nom d'origine", max_length=255)
    mime_type = models.CharField("type MIME détecté", max_length=100)
    size_bytes = models.PositiveBigIntegerField("taille (octets)")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
        verbose_name="client",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="images_uploaded",
        verbose_name="importée par",
    )
    status = models.CharField(
        "statut de traitement",
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    created_at = models.DateTimeField("ajoutée le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class Conversion(models.Model):
    """Traitement appliqué à une image source (extraction texte ou tableau)."""

    class ConversionType(models.TextChoices):
        TEXT = "text", "Image vers texte"
        TABLE = "table", "Image vers tableau"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        RUNNING = "running", "En cours"
        DONE = "done", "Terminée"
        FAILED = "failed", "Échouée"

    image = models.ForeignKey(
        SourceImage,
        on_delete=models.CASCADE,
        related_name="conversions",
        verbose_name="image source",
    )
    conversion_type = models.CharField(
        "type", max_length=10, choices=ConversionType.choices
    )
    status = models.CharField(
        "statut", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField("message d'erreur", blank=True)
    model_used = models.CharField("modèle utilisé", max_length=120, blank=True)
    duration_ms = models.PositiveIntegerField(
        "durée (ms)", null=True, blank=True
    )
    raw_response = models.TextField("réponse brute", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="conversions",
        verbose_name="lancée par",
    )
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    finished_at = models.DateTimeField("terminée le", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_conversion_type_display()} #{self.pk} — {self.image}"


class ExtractedText(models.Model):
    """Texte extrait d'une image, avec version brute et corrigée."""

    class ValidationStatus(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        VALIDATED = "validated", "Validé"
        REJECTED = "rejected", "Rejeté"

    conversion = models.OneToOneField(
        Conversion,
        on_delete=models.CASCADE,
        related_name="extracted_text",
        verbose_name="conversion",
    )
    raw_text = models.TextField("texte brut extrait", blank=True)
    corrected_text = models.TextField("texte corrigé", blank=True)
    language = models.CharField("langue détectée", max_length=20, blank=True)
    validation_status = models.CharField(
        "statut de validation",
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def final_text(self):
        return self.corrected_text if self.corrected_text else self.raw_text


class ExtractedTable(models.Model):
    """Tableau extrait d'une image, stocké en JSON structuré."""

    class ValidationStatus(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        VALIDATED = "validated", "Validé"
        REJECTED = "rejected", "Rejeté"

    conversion = models.OneToOneField(
        Conversion,
        on_delete=models.CASCADE,
        related_name="extracted_table",
        verbose_name="conversion",
    )
    # Format : {"headers": [...], "rows": [[...], ...]}
    raw_data = models.JSONField("données brutes", default=dict, blank=True)
    corrected_data = models.JSONField(
        "données corrigées", default=dict, blank=True
    )
    validation_status = models.CharField(
        "statut de validation",
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def final_data(self):
        return self.corrected_data if self.corrected_data else self.raw_data


class QualityCheck(models.Model):
    """Contrôle qualité d'une conversion : alertes automatiques + décision humaine."""

    class Decision(models.TextChoices):
        NONE = "none", "Aucune"
        VALIDATED = "validated", "Validée"
        REJECTED = "rejected", "Rejetée"

    conversion = models.OneToOneField(
        Conversion,
        on_delete=models.CASCADE,
        related_name="quality_check",
        verbose_name="conversion",
    )
    confidence_score = models.FloatField(
        "score de confiance heuristique (0-1)", null=True, blank=True
    )
    alerts = models.JSONField("alertes", default=list, blank=True)
    decision = models.CharField(
        "décision", max_length=20, choices=Decision.choices, default=Decision.NONE
    )
    decision_comment = models.TextField("commentaire", blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_decisions",
        verbose_name="décidée par",
    )
    decided_at = models.DateTimeField("décidée le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
