from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": "HOPE",
            "link": "https://hope.unicef.org",
        },
        {
            "icon": "diamond",
            "title": "Reporting",
            "link": "https://reporting.hope.unicef.org",
        },
        # ...
    ],
    "LOGIN": {
        "image": lambda request: static("images/hope_logo.png"),
        "redirect_after": lambda request: reverse_lazy("admin:index"),
    },
    "ENVIRONMENT": "hope_documents.config.fragments.unfold.environment_callback",  # environment name in header
    "SHOW_HISTORY": True,
    "SITE_TITLE": "HOPE Documents: ",
    "SITE_HEADER": "HOPE Documents",
    "SITE_SUBHEADER": "",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/x-icon",
            "href": lambda request: static("images/hope_logo.png"),
        },
        {
            "rel": "icon",
            "sizes": "64x64",
            "type": "image/x-icon",
            "href": lambda request: static("images/hope_logo.png"),
        },
    ],
    "SITE_SYMBOL": "speed",  # symbol from icon set
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": lambda request: static("images/hope_logo.png"),  # light mode
        "dark": lambda request: static("images/hope_logo.png"),  # dark mode
    },
    "STYLES": [],
    "BORDER_RADIUS": "6px",
    "COLORS": {
        "base": {
            "50": "249, 250, 251",  # grigi chiari (default neutral)
            "100": "243, 244, 246",
            "200": "229, 231, 235",
            "300": "209, 213, 219",
            "400": "156, 163, 175",
            "500": "107, 114, 128",
            "600": "75, 85, 99",
            "700": "55, 65, 81",
            "800": "31, 41, 55",
            "900": "17, 24, 39",
            "950": "3, 7, 18",
        },
        "primary": {
            "50": "235, 248, 253",  # blu chiarissimo
            "100": "209, 237, 250",
            "200": "163, 219, 245",
            "300": "117, 201, 240",
            "400": "71, 183, 235",
            "500": "28, 171, 226",  # UNICEF Blue ufficiale
            "600": "24, 148, 196",
            "700": "20, 125, 160",
            "800": "16, 101, 129",
            "900": "12, 77, 98",
            "950": "8, 54, 68",
        },
    },
    # https://fonts.google.com/icons
    "SIDEBAR": {
        "show_search": True,  # Search in applications and models names
        "show_all_applications": True,  # Dropdown with all applications and models
        "navigation": [
            {
                "title": _("Security"),
                "separator": True,  # Top border
                "collapsible": False,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Users"),
                        "link": reverse_lazy("admin:hope_documents_user_changelist"),
                    },
                    {
                        "title": _("Groups"),
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": _("Configuration"),
                "separator": True,  # Top border
                "collapsible": False,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Constance"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:constance_config_changelist"),
                    },
                    {
                        "title": _("Flags"),
                        "icon": "done",
                        "link": reverse_lazy("admin:flags_flagstate_changelist"),
                    },
                ],
            },
        ],
    },
}


def badge_callback(request: HttpRequest) -> str:
    return ""


def environment_callback(request: "HttpRequest") -> tuple[str, str]:
    return settings.ENVIRONMENT, "info"
