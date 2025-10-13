import pytest
from demo.factories import get_factory_for_model
from django.apps import apps


@pytest.mark.django_db
@pytest.mark.parametrize("model", ["Country", "DocumentType", "DocumentRule"])
def test_str(model):
    m = apps.get_model("archive", model)
    f = get_factory_for_model(m)
    assert str(f())
