import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from factories import get_factory_for_model
from factories.documents import AttributeFactory, DocumentAttributeFactory, DocumentFactory

from hope_ocr.archive.models import Attribute, Document, DocumentAttribute


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model", ["Country", "DocumentType", "DocumentRule", "Attribute", "Document", "DocumentAttribute"]
)
def test_str(model):
    m = apps.get_model("archive", model)
    f = get_factory_for_model(m)
    assert str(f.create())


@pytest.fixture
def document_attribute():
    return DocumentAttributeFactory.create()


@pytest.fixture
def document():
    return DocumentFactory.create()


@pytest.fixture
def system_attribute():
    return AttributeFactory.create(system=True)


@pytest.fixture
def custom_attribute():
    return AttributeFactory.create(system=False)


@pytest.mark.django_db
def test_clean_on_new_attribute_is_noop():
    attr = Attribute(name="new_attr", system=False)
    attr.full_clean()


@pytest.mark.django_db
def test_document_attribute_duplicate_blocked(document_attribute):
    with pytest.raises(IntegrityError):
        DocumentAttribute.objects.create(document=document_attribute.document, attribute=document_attribute.attribute)


@pytest.mark.django_db
def test_document_duplicate_blocked(document):
    with pytest.raises(IntegrityError):
        Document.objects.create(
            document_type=document.document_type,
            country=document.country,
            version=document.version,
        )


@pytest.mark.django_db
def test_system_attribute_name_cannot_change(system_attribute):
    system_attribute.name = "changed_name"
    with pytest.raises(ValidationError):
        system_attribute.full_clean()


@pytest.mark.django_db
def test_system_attribute_description_can_change(system_attribute):
    system_attribute.description = "updated description"
    system_attribute.full_clean()
    system_attribute.save()
    system_attribute.refresh_from_db()
    assert system_attribute.description == "updated description"


@pytest.mark.django_db
def test_system_attribute_cannot_be_deleted(system_attribute):
    with pytest.raises(ProtectedError):
        system_attribute.delete()


@pytest.mark.django_db
def test_custom_attribute_can_be_deleted(custom_attribute):
    pk = custom_attribute.pk
    custom_attribute.delete()
    assert not Attribute.objects.filter(pk=pk).exists()
