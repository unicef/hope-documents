import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from factories import get_factory_for_model
from factories.documents import AttributeFactory, DocumentAttributeFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model", ["Country", "DocumentType", "DocumentRule", "Attribute", "Document", "DocumentAttribute"]
)
def test_str(model):
    m = apps.get_model("archive", model)
    f = get_factory_for_model(m)
    assert str(f())


@pytest.mark.django_db
def test_document_attribute_duplicate_blocked():
    from hope_ocr.archive.models import DocumentAttribute

    da = DocumentAttributeFactory()
    with pytest.raises(IntegrityError):
        DocumentAttribute.objects.create(document=da.document, attribute=da.attribute)


@pytest.mark.django_db
def test_system_attribute_name_cannot_change():
    attr = AttributeFactory(system=True)
    attr.name = "changed_name"
    with pytest.raises(ValidationError):
        attr.full_clean()


@pytest.mark.django_db
def test_system_attribute_description_can_change():
    attr = AttributeFactory(system=True)
    attr.description = "updated description"
    attr.full_clean()
    attr.save()
    attr.refresh_from_db()
    assert attr.description == "updated description"


@pytest.mark.django_db
def test_system_attribute_cannot_be_deleted():
    attr = AttributeFactory(system=True)
    with pytest.raises(ProtectedError):
        attr.delete()


@pytest.mark.django_db
def test_custom_attribute_can_be_deleted():
    attr = AttributeFactory(system=False)
    pk = attr.pk
    attr.delete()
    assert not apps.get_model("archive", "Attribute").objects.filter(pk=pk).exists()
