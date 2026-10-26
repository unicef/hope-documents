from io import StringIO

import pytest
from django.core.management import call_command

from hope_ocr.archive.models import Country, Document, DocumentAttribute, DocumentType


@pytest.mark.django_db
def test_demo_data_creates_all_objects():
    stdout = StringIO()
    call_command("demo_data", stdout=stdout)

    assert Country.objects.filter(code2="IT").exists()
    assert DocumentType.objects.filter(code="DL").exists()
    assert DocumentType.objects.filter(code="PAS").exists()
    assert Document.objects.filter(document_type__code="DL", country__code2="IT").exists()
    assert Document.objects.filter(document_type__code="PAS", country__code2="IT").exists()
    assert DocumentAttribute.objects.count() == 6  # 3 attrs × 2 doc types
    assert "Demo data ready" in stdout.getvalue()


@pytest.mark.django_db
def test_demo_data_idempotent():
    """Running demo_data twice must not duplicate any objects."""
    call_command("demo_data", stdout=StringIO())
    call_command("demo_data", stdout=StringIO())

    assert Document.objects.count() == 2
    assert DocumentAttribute.objects.count() == 6


@pytest.mark.django_db
def test_demo_data_missing_system_attributes():
    """If system attributes are absent the command prints an error and exits early."""
    from hope_ocr.archive.models import Attribute

    Attribute.objects.filter(system=True).delete()

    stdout = StringIO()
    call_command("demo_data", stdout=stdout)

    assert "Missing system attributes" in stdout.getvalue()
    # Documents are created before the system-attrs check, but no DocumentAttributes are seeded
    assert DocumentAttribute.objects.count() == 0
