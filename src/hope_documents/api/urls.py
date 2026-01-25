from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .router import Router
from .viewsets import ExtractView, GroupViewSet, UserViewSet

app_name = "api"

router = Router()
router.register(r"users", UserViewSet, basename="user")
router.register(r"groups", GroupViewSet, basename="group")


urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("upload/", ExtractView.as_view(), name="file-upload"),
    path("", include(router.urls)),
]
