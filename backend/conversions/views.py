import csv
import io

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Conversion, ExtractedTable, ExtractedText, QualityCheck, SourceImage
from .serializers import (
    ConversionSerializer,
    DecideSerializer,
    ExtractedTableSerializer,
    ExtractedTextSerializer,
    ImageUploadSerializer,
    SourceImageSerializer,
)
from .services import run_conversion


class SourceImageViewSet(viewsets.ModelViewSet):
    serializer_class = SourceImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["original_name", "client__name"]
    ordering_fields = ["created_at", "original_name", "size_bytes"]

    def get_queryset(self):
        qs = SourceImage.objects.select_related("client", "uploaded_by")
        params = self.request.query_params
        if params.get("client"):
            qs = qs.filter(client_id=params["client"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]
        image = SourceImage.objects.create(
            file=f,
            original_name=f.name,
            mime_type=serializer._detected_mime,
            size_bytes=f.size,
            width=serializer._width,
            height=serializer._height,
            client=serializer.validated_data.get("client"),
            uploaded_by=request.user,
        )
        return Response(
            SourceImageSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Lance une conversion 'text' ou 'table' sur l'image (synchrone)."""
        image = self.get_object()
        conv_type = request.data.get("type")
        if conv_type not in (Conversion.ConversionType.TEXT,
                             Conversion.ConversionType.TABLE):
            return Response(
                {"detail": "Type invalide : 'text' ou 'table' attendu."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conversion = Conversion.objects.create(
            image=image, conversion_type=conv_type, created_by=request.user
        )
        run_conversion(conversion)
        return Response(
            ConversionSerializer(conversion, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConversionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversionSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "finished_at"]

    def get_queryset(self):
        qs = (
            Conversion.objects
            .select_related("image", "image__client", "created_by",
                            "extracted_text", "extracted_table", "quality_check")
        )
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("type"):
            qs = qs.filter(conversion_type=params["type"])
        if params.get("client"):
            qs = qs.filter(image__client_id=params["client"])
        if params.get("image"):
            qs = qs.filter(image_id=params["image"])
        return qs

    @action(detail=True, methods=["patch"], url_path="text")
    def update_text(self, request, pk=None):
        """Corrige le texte extrait d'une conversion."""
        conversion = self.get_object()
        try:
            text = conversion.extracted_text
        except ExtractedText.DoesNotExist:
            return Response(
                {"detail": "Cette conversion n'a pas de texte extrait."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ExtractedTextSerializer(text, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if "validation_status" in serializer.validated_data:
            return Response(
                {"detail": "Utilisez /decide/ pour valider ou rejeter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="table")
    def update_table(self, request, pk=None):
        """Corrige le tableau extrait (en-têtes/lignes) d'une conversion."""
        conversion = self.get_object()
        try:
            table = conversion.extracted_table
        except ExtractedTable.DoesNotExist:
            return Response(
                {"detail": "Cette conversion n'a pas de tableau extrait."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data.get("corrected_data")
        if data is not None:
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            if not isinstance(headers, list) or not isinstance(rows, list):
                return Response(
                    {"detail": "Format attendu : {headers: [...], rows: [[...]]}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            table.corrected_data = {"headers": headers, "rows": rows}
            table.save(update_fields=["corrected_data", "updated_at"])
        return Response(ExtractedTableSerializer(table).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        """Décision humaine de contrôle qualité : valider ou rejeter."""
        conversion = self.get_object()
        serializer = DecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        comment = serializer.validated_data.get("comment", "")

        qc, _ = QualityCheck.objects.get_or_create(conversion=conversion)
        qc.decision = decision
        qc.decision_comment = comment
        qc.decided_by = request.user
        qc.decided_at = timezone.now()
        qc.save()

        status_map = {
            "validated": ExtractedText.ValidationStatus.VALIDATED,
            "rejected": ExtractedText.ValidationStatus.REJECTED,
        }
        target_status = status_map[decision]
        for rel in ("extracted_text", "extracted_table"):
            obj = getattr(conversion, rel, None)
            if obj is not None:
                obj.validation_status = target_status
                obj.save(update_fields=["validation_status", "updated_at"])

        return Response(
            ConversionSerializer(conversion, context={"request": request}).data
        )

    @action(detail=True, methods=["get"])
    def export_csv(self, request, pk=None):
        """Exporte le tableau extrait (corrigé si présent) au format CSV."""
        conversion = self.get_object()
        try:
            table = conversion.extracted_table
        except ExtractedTable.DoesNotExist:
            return Response(
                {"detail": "Cette conversion n'a pas de tableau extrait."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = table.final_data or {}
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        if data.get("headers"):
            writer.writerow(data["headers"])
        for row in data.get("rows", []):
            writer.writerow(row)
        # utf-8-sig ajoute le BOM pour qu'Excel détecte correctement l'UTF-8.
        response = HttpResponse(
            "\ufeff" + buffer.getvalue(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="conversion_{conversion.pk}.csv"'
        )
        return response

    @action(detail=True, methods=["get"])
    def export_xlsx(self, request, pk=None):
        """Exporte le tableau extrait (corrigé si présent) au format Excel .xlsx."""
        from openpyxl import Workbook

        conversion = self.get_object()
        try:
            table = conversion.extracted_table
        except ExtractedTable.DoesNotExist:
            return Response(
                {"detail": "Cette conversion n'a pas de tableau extrait."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = table.final_data or {}
        wb = Workbook()
        ws = wb.active
        ws.title = "Extraction"
        if data.get("headers"):
            ws.append([str(h) for h in data["headers"]])
        for row in data.get("rows", []):
            ws.append([str(c) for c in row])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="conversion_{conversion.pk}.xlsx"'
        )
        return response

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Relance une conversion échouée."""
        conversion = self.get_object()
        if conversion.status == Conversion.Status.RUNNING:
            return Response(
                {"detail": "Conversion déjà en cours."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run_conversion(conversion)
        return Response(
            ConversionSerializer(conversion, context={"request": request}).data
        )
