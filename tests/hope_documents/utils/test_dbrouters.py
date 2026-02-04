from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from hope_documents.utils.dbrouters import DbRouter


@pytest.fixture
def router():
    return DbRouter()


@override_settings(DATABASE_APPS_MAPPING={"my_app": "my_db"})
def test_select_db_mapped_app(router):
    """Test that select_db returns the correct db for a mapped app."""
    model = MagicMock()
    model._meta.app_label = "my_app"
    model._meta.proxy = False
    assert router.select_db(model) == "my_db"


@override_settings(DATABASE_APPS_MAPPING={"my_app": "my_db"})
def test_select_db_unmapped_app(router):
    """Test that select_db returns None for an unmapped app."""
    model = MagicMock()
    model._meta.app_label = "another_app"
    model._meta.proxy = False
    assert router.select_db(model) is None


@override_settings(DATABASE_APPS_MAPPING={"my_app": "my_db"})
def test_select_db_proxy_model(router):
    """Test that select_db works correctly with proxy models."""
    proxied_model = MagicMock()
    proxied_model._meta.app_label = "my_app"
    model = MagicMock()
    model._meta.proxy = True
    model._meta.proxy_for_model = proxied_model
    assert router.select_db(model) == "my_db"


def test_select_db_no_model(router):
    """Test that select_db returns None when no model is provided."""
    assert router.select_db(None) is None


@patch("hope_documents.utils.dbrouters.DbRouter.select_db")
def test_db_for_read(mock_select_db, router):
    """Test that db_for_read calls select_db."""
    model = MagicMock()
    router.db_for_read(model)
    mock_select_db.assert_called_once_with(model)


@patch("hope_documents.utils.dbrouters.DbRouter.select_db")
def test_db_for_write(mock_select_db, router):
    """Test that db_for_write calls select_db."""
    model = MagicMock()
    router.db_for_write(model)
    mock_select_db.assert_called_once_with(model)


@pytest.mark.parametrize("db_name", ["hope", "hope_ro"])
def test_allow_migrate_hope_db(router, db_name):
    """Test that migrations are not allowed on 'hope' or 'hope_ro' dbs."""
    assert not router.allow_migrate(db_name, "any_app")


@override_settings(DATABASE_APPS_MAPPING={"mapped_app": "mapped_db"})
def test_allow_migrate_default_db_unmapped_app(router):
    """
    Test that migrations are allowed on the 'default' db for unmapped apps.
    """
    assert router.allow_migrate("default", "unmapped_app")


@override_settings(DATABASE_APPS_MAPPING={"mapped_app": "mapped_db"})
def test_allow_migrate_mapped_app_correct_db(router):
    """Test that migrations are allowed for a mapped app on the correct db."""
    assert router.allow_migrate("mapped_db", "mapped_app")


@override_settings(DATABASE_APPS_MAPPING={"mapped_app": "mapped_db"})
def test_allow_migrate_mapped_app_incorrect_db(router):
    """Test that migrations are not allowed for a mapped app on an incorrect db."""
    assert not router.allow_migrate("another_db", "mapped_app")
