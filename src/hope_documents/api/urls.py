from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from .viewsets import ExtractView, GroupViewSet, UserViewSet

app_name = "api"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"groups", GroupViewSet, basename="group")


urlpatterns = [
    path("rest/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "rest/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger",
    ),
    path("rest/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("upload/", ExtractView.as_view(), name="file-upload"),
    path("", include(router.urls)),
]
