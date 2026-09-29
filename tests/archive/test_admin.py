from pathlib import Path

import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from factories.documents import AttributeFactory
from webtest import Upload

from hope_ocr.archive.admin import AttributeAdmin
from hope_ocr.archive.models import Attribute
from hope_ocr.ocr.engine import MatchMode


@pytest.fixture
def attribute_admin():
    return AttributeAdmin(Attribute, AdminSite())


@pytest.fixture
def system_attr():
    return AttributeFactory.create(system=True)


@pytest.mark.django_db
def test_attribute_admin_readonly_fields_for_system(attribute_admin, system_attr):
    assert attribute_admin.get_readonly_fields(None, obj=system_attr) == ["name", "system"]


@pytest.mark.django_db
def test_attribute_admin_readonly_fields_for_new_object(attribute_admin):
    assert attribute_admin.get_readonly_fields(None, obj=None) == ["system"]


@pytest.fixture
def document1(images_dir):
    image_file = Path(images_dir / "ita/dl1.png")
    with image_file.open("b+r") as f:
        return Upload(str(image_file.absolute()), f.read(), "image/png")


@pytest.mark.django_db
def test_scan_image_find(app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1

    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Document processed" in res.content


@pytest.mark.django_db
def test_scan_image_search_found(app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1
    res.forms["scan-form"]["target"] = "MO1699252K"
    res.forms["scan-form"]["max_errors"] = "5"
    res.forms["scan-form"]["mode"] = MatchMode.FIRST.value
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Text found" in res.content, res.showbrowser()


@pytest.mark.django_db
def test_scan_image_search_not_found(app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1
    res.forms["scan-form"]["target"] = "---"
    res.forms["scan-form"]["max_errors"] = "0"
    res.forms["scan-form"]["mode"] = MatchMode.FIRST.value
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Text not found" in res.content


@pytest.mark.django_db
def test_scan_image_form_invalid(app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = app.get(url, user=admin_user)
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"This field is required." in res.content


@pytest.mark.django_db
def test_scan_image_search_all(app, admin_user, document1):
    url = reverse("admin:archive_documentrule_scan_image")

    res = app.get(url, user=admin_user)
    res.forms["scan-form"]["image"] = document1
    res.forms["scan-form"]["target"] = "MO1699252K"
    res.forms["scan-form"]["mode"] = MatchMode.ALL.value
    res = res.forms["scan-form"].submit()
    assert res.status_code == 200
    assert b"Text found" in res.content
