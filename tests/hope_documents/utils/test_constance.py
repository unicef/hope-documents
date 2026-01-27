from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.forms import TextInput, Textarea

from hope_documents.utils.constance import (
    GroupSelect,
    WriteOnlyInput,
    WriteOnlyTextarea,
    WriteOnlyWidget,
)


@pytest.mark.django_db
class TestGroupSelect:
    def test_group_select_initialization_no_groups(self):
        # Act
        field = GroupSelect()

        # Assert
        assert field.choices == [("", "None")]

    def test_group_select_initialization_with_groups(self):
        # Arrange
        group1 = Group.objects.create(name="Admins")
        group2 = Group.objects.create(name="Users")

        # Act
        field = GroupSelect()

        # Assert
        choices_as_set = set(field.choices)
        expected_choices_as_set = {
            ("", "None"),
            (group1.pk, "Admins"),
            (group2.pk, "Users"),
        }
        assert choices_as_set == expected_choices_as_set


class TestWriteOnlyWidget:
    def test_format_value(self):
        # Arrange
        widget = WriteOnlyWidget()

        # Act
        formatted_value = widget.format_value("some_secret_value")

        # Assert
        assert formatted_value == "***"

    def test_format_value_with_none(self):
        # Arrange
        widget = WriteOnlyWidget()

        # Act
        formatted_value = widget.format_value(None)

        # Assert
        assert formatted_value == "***"

    @patch("hope_documents.utils.constance.config")
    def test_value_from_datadict_is_hidden(self, mock_config):
        # Arrange
        widget = WriteOnlyWidget()
        data = {"A_SECRET_KEY": "***"}
        files = {}
        name = "A_SECRET_KEY"

        # Configure the mock to have the attribute that will be requested.
        mock_config.A_SECRET_KEY = "my_secret_from_config"

        # Act
        value = widget.value_from_datadict(data, files, name)

        # Assert
        assert value == "my_secret_from_config"

    @patch("hope_documents.utils.constance.config")
    def test_value_from_datadict_is_new_value(self, mock_config):
        # Arrange
        widget = WriteOnlyWidget()
        data = {"A_SECRET_KEY": "new_secret_value"}
        files = {}
        name = "A_SECRET_KEY"

        # Act
        value = widget.value_from_datadict(data, files, name)

        # Assert
        assert value == "new_secret_value"
        # ensure config is not touched
        assert not mock_config.mock_calls


class TestWriteOnlyMixins:
    def test_write_only_textarea_instantiation(self):
        widget = WriteOnlyTextarea()
        assert isinstance(widget, WriteOnlyWidget)
        assert isinstance(widget, Textarea)

    def test_write_only_input_instantiation(self):
        widget = WriteOnlyInput()
        assert isinstance(widget, WriteOnlyWidget)
        assert isinstance(widget, TextInput)
