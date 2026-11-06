from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
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
def test_define_regions_get_region_serialized_in_json(app):
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.get(url)
    assert b"top_left" in res.content


@pytest.mark.django_db
def test_define_regions_get_has_zoom_controls(app):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.get(url)
    assert b"zoom-controls" in res.content
    assert b"canvas-wrapper" in res.content


@pytest.mark.django_db
def test_test_regions_get(app):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    res = app.get(url)
    assert res.status_code == 200
    assert da.attribute.name.encode() in res.content


@pytest.mark.django_db
def test_test_regions_get_has_canvas_and_json(app):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    res = app.get(url)
    assert b"test-canvas" in res.content
    assert b"DOC_ATTRS" in res.content


@pytest.mark.django_db
def test_test_regions_post_with_region(app, images_dir):
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with image_path.open("rb") as f:
        res = app.post(url, {"image": Upload(str(image_path), f.read(), "image/png")})
    assert res.status_code == 200
    assert b"region-yes" in res.content


@pytest.mark.django_db
def test_test_regions_post_with_image(app, images_dir):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with image_path.open("rb") as f:
        res = app.post(url, {"image": Upload(str(image_path), f.read(), "image/png")})
    assert res.status_code == 200
    assert da.attribute.name.encode() in res.content
    assert b"results-table" in res.content


@pytest.mark.django_db
def test_test_regions_post_no_image(app):
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    res = app.post(url, {})
    assert res.status_code == 200
    assert da.attribute.name.encode() in res.content


@pytest.mark.django_db
def test_test_regions_post_validation_pass(app, images_dir):
    da = DocumentAttributeFactory.create(validation_expression=r"\w+")
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with patch("hope_documents.archive.admin.OCRAttributeExtractor.extract_attribute", return_value="BIANCA"):
        with image_path.open("rb") as f:
            res = app.post(url, {"image": Upload(str(image_path), f.read(), "image/png")})
    assert res.status_code == 200
    assert b"val-pass" in res.content


@pytest.mark.django_db
def test_test_regions_post_validation_fail(app, images_dir):
    da = DocumentAttributeFactory.create(validation_expression=r"\d+")
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with patch("hope_documents.archive.admin.OCRAttributeExtractor.extract_attribute", return_value="BIANCA"):
        with image_path.open("rb") as f:
            res = app.post(url, {"image": Upload(str(image_path), f.read(), "image/png")})
    assert res.status_code == 200
    assert b"val-fail" in res.content


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
def test_document_attribute_inline_formfield_applies_unfold_widget_to_regex_field():
    """formfield_for_dbfield replaces the widget on RegexField with UnfoldAdminTextInputWidget."""
    from unfold.widgets import UnfoldAdminTextInputWidget

    inline = DocumentAttributeInline(DocumentAttribute, AdminSite())
    request = RequestFactory().get("/")
    db_field = DocumentAttribute._meta.get_field("validation_expression")
    formfield = inline.formfield_for_dbfield(db_field, request)
    assert isinstance(formfield.widget, UnfoldAdminTextInputWidget)


@pytest.mark.django_db
def test_test_regions_post_preprocesses_image(app, images_dir):
    """test_regions pre-processes the uploaded image; the base64 image_src reflects the processed image."""
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with patch("hope_documents.archive.admin.detect_and_normalise") as mock_preprocess:
        processed = Image.new("RGB", (100, 80), (200, 200, 200))
        mock_preprocess.return_value = processed
        with image_path.open("rb") as f:
            res = app.post(url, {"image": Upload(str(image_path), f.read(), "image/png")})
    assert res.status_code == 200
    mock_preprocess.assert_called_once()


@pytest.mark.django_db
def test_test_regions_scales_region_by_reference_dims(app, images_dir):
    """When Document has reference dims, regions passed to the extractor are scaled."""
    bb = BoundingBox.from_rect(10, 20, 100, 50)
    da = DocumentAttributeFactory.create(region=bb)
    da.document.reference_width = 200
    da.document.reference_height = 100
    da.document.save(update_fields=["reference_width", "reference_height"])
    url = reverse("admin:archive_document_test_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"

    captured_regions = []

    def fake_extract(self_inner, image, attr_name, region):
        captured_regions.append(region)
        return "test_value"

    with patch("hope_documents.archive.admin.detect_and_normalise") as mock_preprocess:
        mock_preprocess.return_value = Image.new("RGB", (400, 300), (200, 200, 200))
        with patch("hope_documents.archive.admin.OCRAttributeExtractor.extract_attribute", fake_extract):
            with image_path.open("rb") as f:
                res = app.post(url, {"image": Upload(str(image_path), f.read(), "image/png")})

    assert res.status_code == 200
    assert len(captured_regions) == 1
    # scale: 400/200=2.0, 300/100=3.0
    scaled = captured_regions[0]
    assert scaled is not None
    assert scaled.top_left.x == pytest.approx(20.0)  # 10 * 2.0
    assert scaled.top_left.y == pytest.approx(60.0)  # 20 * 3.0


@pytest.mark.django_db
def test_define_regions_get_has_reference_dim_inputs(app):
    """GET define_regions renders hidden reference_width/height inputs in the save form."""
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.get(url)
    assert b'name="reference_width"' in res.content
    assert b'name="reference_height"' in res.content


@pytest.mark.django_db
def test_define_regions_post_image_returns_json(app, images_dir):
    """POSTing an image to define_regions returns JSON with image_src, width, height."""
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    image_path = images_dir / "ita/dl1.png"
    with image_path.open("rb") as f:
        res = app.post(url, {"image": Upload(str(image_path.absolute()), f.read(), "image/png")})
    assert res.status_code == 200
    assert res.content_type == "application/json"
    data = res.json
    assert "image_src" in data
    assert "width" in data
    assert "height" in data
    assert data["width"] > 0
    assert data["height"] > 0


@pytest.mark.django_db
def test_define_regions_post_saves_reference_dims(app):
    """POST save-regions with reference_width/height updates the Document."""
    da = DocumentAttributeFactory.create()
    url = reverse("admin:archive_document_define_regions", args=[da.document.pk])
    res = app.post(
        url,
        {
            f"region_{da.pk}_x": "10",
            f"region_{da.pk}_y": "20",
            f"region_{da.pk}_width": "100",
            f"region_{da.pk}_height": "50",
            "reference_width": "1200",
            "reference_height": "900",
        },
    )
    assert res.status_code == 200
    da.document.refresh_from_db()
    assert da.document.reference_width == 1200
    assert da.document.reference_height == 900


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
