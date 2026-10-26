from pathlib import Path

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse
from factories.documents import AttributeFactory, DocumentAttributeFactory
from webtest import Upload

from hope_documents.archive.admin import AttributeAdmin, DocumentAttributeInline
from hope_documents.archive.models import Attribute, DocumentAttribute
from hope_documents.archive.region import BoundingBox
from hope_documents.ocr.engine import MatchMode


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


@pytest.mark.django_db
def test_define_regions_get(app):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.get(url)
    assert res.status_code == 200
    assert da.attribute.name.encode() in res.content


@pytest.mark.django_db
def test_define_regions_post_image_upload(app, images_dir):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with image_path.open("rb") as f:
        res = app.post(url, {"image": Upload(str(image_path.absolute()), f.read(), "image/png")})
    assert res.status_code == 200
    assert b"region-canvas" in res.content


@pytest.mark.django_db
def test_define_regions_post_save_coords(app):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.post(
        url,
        {
            f"region_{da.pk}_x": "10",
            f"region_{da.pk}_y": "20",
            f"region_{da.pk}_width": "100",
            f"region_{da.pk}_height": "50",
        },
    )
    assert res.status_code == 200
    da.refresh_from_db()
    assert da.region == BoundingBox.from_rect(10, 20, 100, 50)


@pytest.mark.django_db
def test_define_regions_post_clear_coords(app):
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.post(
        url,
        {
            f"region_{da.pk}_x": "",
            f"region_{da.pk}_y": "",
            f"region_{da.pk}_width": "",
            f"region_{da.pk}_height": "",
        },
    )
    assert res.status_code == 200
    da.refresh_from_db()
    assert da.region is None


@pytest.mark.django_db
def test_define_regions_post_save_coords_preserves_image_src(app):
    """When coords are saved and image_src is in the POST body, it is echoed back into the response."""
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.post(
        url,
        {
            f"region_{da.pk}_x": "10",
            f"region_{da.pk}_y": "20",
            f"region_{da.pk}_width": "100",
            f"region_{da.pk}_height": "50",
            "image_src": "data:image/png;base64,TESTTOKEN",
        },
    )
    assert res.status_code == 200
    assert b"TESTTOKEN" in res.content


@pytest.mark.django_db
def test_document_attribute_inline_formfield_applies_unfold_widget_to_regex_field():
    """formfield_for_dbfield replaces the widget on RegexField with UnfoldAdminTextInputWidget."""
    from unfold.widgets import UnfoldAdminTextInputWidget

    inline = DocumentAttributeInline(DocumentAttribute, AdminSite())
    request = RequestFactory().get("/")
    db_field = DocumentAttribute._meta.get_field("validation_expression")
    formfield = inline.formfield_for_dbfield(db_field, request)
    assert isinstance(formfield.widget, UnfoldAdminTextInputWidget)


@pytest.mark.django_db
def test_document_attribute_inline_formfield_non_regex_field_unchanged():
    """formfield_for_dbfield leaves non-RegexField fields untouched."""
    from unfold.widgets import UnfoldAdminTextInputWidget

    inline = DocumentAttributeInline(DocumentAttribute, AdminSite())
    request = RequestFactory().get("/")
    db_field = DocumentAttribute._meta.get_field("region")
    formfield = inline.formfield_for_dbfield(db_field, request)
    # region is a JSONField — widget must NOT be replaced with UnfoldAdminTextInputWidget
    assert not isinstance(formfield.widget, UnfoldAdminTextInputWidget)
