from django.conf import settings
from django.contrib.admin import site
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("api/", include("hope_documents.api.urls"), name="api"),
    path("favicon.ico", serve, kwargs={"document_root": settings.STATIC_ROOT, "path": "favicon.ico"}),
    path("admin/", site.urls),
    path("social/", include("social_django.urls", namespace="social")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("adminactions/", include("adminactions.urls")),
    path("", include("hope_documents.modules.web.urls")),
]

if settings.DEBUG:
    if "debug_toolbar.middleware.DebugToolbarMiddleware" in settings.MIDDLEWARE:
        import debug_toolbar

        urlpatterns = [
            path(r"__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

    if "django_browser_reload.middleware.BrowserReloadMiddleware" in settings.MIDDLEWARE:
        urlpatterns += [
            path("__reload__/", include("django_browser_reload.urls")),
        ]

urlpatterns = [path(settings.URL_PREFIX, include(urlpatterns))]  # type: ignore[arg-type]
