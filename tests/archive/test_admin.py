from pathlib import Path

import pytest
from django.urls import reverse
from webtest import Upload

from hope_documents.ocr.engine import MatchMode

images_dir = Path(__file__).parent.parent / "images"


@pytest.fixture
def document1():
    with (images_dir / "ita/dl1.png").open("b+r") as f:
        return Upload("file_path.png", f.read(), "image/png")


def test_scan_image_find(django_app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = django_app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1

    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Document processed" in res.content


def test_scan_image_search_found(django_app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = django_app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1
    res.forms["scan-form"]["target"] = "MO1699252K"
    res.forms["scan-form"]["mode"] = MatchMode.FIRST.value
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Text found" in res.content


def test_scan_image_search_not_found(django_app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = django_app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1
    res.forms["scan-form"]["target"] = "555"
    res.forms["scan-form"]["max_errors"] = "0"
    res.forms["scan-form"]["mode"] = MatchMode.FIRST.value
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Text not found" in res.content


def test_scan_image_search_all(django_app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = django_app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1
    res.forms["scan-form"]["target"] = "MO1699252K"
    res.forms["scan-form"]["mode"] = MatchMode.ALL.value
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Text found" in res.content
