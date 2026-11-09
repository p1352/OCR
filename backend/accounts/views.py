from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdmin
from .serializers import (
    MeSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Administration des comptes — réservé aux administrateurs."""

    queryset = User.objects.all().order_by("username")
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        # Désactivation plutôt que suppression pour préserver la traçabilité.
        user = self.get_object()
        if user == request.user:
            return Response(
                {"detail": "Vous ne pouvez pas désactiver votre propre compte."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == "PATCH":
        allowed = {"first_name", "last_name", "email"}
        for field in allowed:
            if field in request.data:
                setattr(request.user, field, request.data[field])
        request.user.save()
    return Response(MeSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    old = request.data.get("old_password", "")
    new = request.data.get("new_password", "")
    if not request.user.check_password(old):
        return Response(
            {"detail": "Ancien mot de passe incorrect."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        validate_password(new, user=request.user)
    except Exception as exc:
        return Response(
            {"detail": " ".join(exc.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    request.user.set_password(new)
    request.user.save()
    return Response({"detail": "Mot de passe modifié."})


class LaurentTokenObtainPairView(TokenObtainPairView):
    """Connexion JWT — renvoie aussi le profil de l'utilisateur."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            from django.contrib.auth import authenticate
            user = authenticate(
                request,
                username=request.data.get("username"),
                password=request.data.get("password"),
            )
            if user:
                response.data["user"] = MeSerializer(user).data
        return response
