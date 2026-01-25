import pytest
from django.db import models, connection
from django.apps import apps
from django.conf import settings

from hope_documents.models.base import AbstractModel, BaseManager
import time


@pytest.fixture(scope="module")
def concrete_model(django_db_blocker):
    with django_db_blocker.unblock():
        # Define a temporary app and model
        test_app_name = "test_app_for_abstract_model"

        # Ensure the app is not already installed (important for re-runs in a session)
        if test_app_name in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != test_app_name]
            apps.clear_cache()

        settings.INSTALLED_APPS += [test_app_name]
        apps.populate(settings.INSTALLED_APPS)

        class ConcreteModel(AbstractModel):
            name = models.CharField(max_length=255)

            class Meta:
                app_label = test_app_name
                app_config = "django.apps.AppConfig"  # Use a generic AppConfig
                managed = False  # Important for dynamically created tables

        # Dynamically add the model to the app registry
        # This is a bit hacky, but necessary for dynamic models outside of real apps
        apps.all_models[test_app_name] = {ConcreteModel._meta.model_name: ConcreteModel}

        # Create table for the temporary model
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ConcreteModel)

        yield ConcreteModel

        # Teardown: Delete the table and unregister the model
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(ConcreteModel)

        # Clean up app registry
        del apps.all_models[test_app_name]
        settings.INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != test_app_name]
        apps.clear_cache()


@pytest.mark.django_db
def test_abstract_model_last_modify_date(concrete_model):
    ConcreteModel = concrete_model  # Get the dynamically created model
    obj = ConcreteModel.objects.create(name="Test Object")
    initial_date = obj.last_modify_date
    assert initial_date is not None

    # Update the object and check if last_modify_date changes
    time.sleep(0.001)  # Ensure a measurable time difference
    obj.name = "Updated Object"
    obj.save()
    obj.refresh_from_db()
    assert obj.last_modify_date > initial_date


@pytest.mark.django_db
def test_abstract_model_objects_manager(concrete_model):
    ConcreteModel = concrete_model  # Get the dynamically created model
    assert isinstance(ConcreteModel.objects, BaseManager)
