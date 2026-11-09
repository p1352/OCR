from django.conf import settings
from django.db import models


class Client(models.Model):
    """Client (personne ou organisation) auquel sont rattachées les données."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Actif"
        ARCHIVED = "archived", "Archivé"

    name = models.CharField("nom / raison sociale", max_length=255)
    email = models.EmailField("e-mail", blank=True)
    phone = models.CharField("téléphone", max_length=50, blank=True)
    address = models.TextField("adresse", blank=True)
    notes = models.TextField("notes", blank=True)
    status = models.CharField(
        "statut", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_created",
        verbose_name="créé par",
    )
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "client"
        verbose_name_plural = "clients"

    def __str__(self):
        return self.name
