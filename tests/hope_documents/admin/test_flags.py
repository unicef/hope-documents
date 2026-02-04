import pytest
from hope_documents.admin.flags import FlagStateForm
from unfold.widgets import CHECKBOX_CLASSES, INPUT_CLASSES


@pytest.mark.django_db
def test_flag_state_form_fields_have_css_classes():
    """Test that the form fields have the correct CSS classes."""
    form = FlagStateForm()
    assert form.fields["name"].widget.attrs["class"] == " ".join(INPUT_CLASSES)
    assert form.fields["condition"].widget.attrs["class"] == " ".join(INPUT_CLASSES)
    assert form.fields["value"].widget.attrs["class"] == " ".join(INPUT_CLASSES)
    assert form.fields["required"].widget.attrs["class"] == " ".join(CHECKBOX_CLASSES)

