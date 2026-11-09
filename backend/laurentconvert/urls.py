from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import LaurentTokenObtainPairView, change_password, me
from clients.views import ClientViewSet
from conversions.views import ConversionViewSet, SourceImageViewSet
from accounts.views import UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("clients", ClientViewSet, basename="client")
router.register("images", SourceImageViewSet, basename="image")
router.register("conversions", ConversionViewSet, basename="conversion")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", LaurentTokenObtainPairView.as_view(), name="token"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", me, name="me"),
    path("api/auth/change-password/", change_password, name="change_password"),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
