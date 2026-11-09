from django.db.models import Count
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from conversions.serializers import SourceImageSerializer, ConversionSerializer

from .models import Client
from .serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = Client.objects.annotate(image_count=Count("images")).order_by("name")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        client = self.get_object()
        client.status = Client.Status.ARCHIVED
        client.save(update_fields=["status"])
        return Response(ClientSerializer(client).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        client = self.get_object()
        client.status = Client.Status.ACTIVE
        client.save(update_fields=["status"])
        return Response(ClientSerializer(client).data)

    @action(detail=True, methods=["get"])
    def images(self, request, pk=None):
        client = self.get_object()
        serializer = SourceImageSerializer(
            client.images.all(), many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def conversions(self, request, pk=None):
        client = self.get_object()
        qs = ConversionSerializer.Meta.model.objects.filter(image__client=client)
        serializer = ConversionSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)
