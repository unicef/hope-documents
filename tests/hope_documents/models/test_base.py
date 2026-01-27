from django.db import models

from hope_documents.models.base import AbstractModel, BaseManager, BaseQuerySet


def test_queryset_instance():
    # This ensures the class can be instantiated.
    # A mock model is needed for the QuerySet constructor.
    mock_model = type(
        'MockModel',
        (models.Model,),
        {
            '__module__': 'tests.hope_documents.models.test_base',
            'Meta': type('Meta', (object,), {'app_label': 'tests_app'}),
        }
    )
    qs = BaseQuerySet(model=mock_model)
    assert isinstance(qs, BaseQuerySet)


def test_manager_instance_and_queryset_class():
    # This ensures the manager can be instantiated and its queryset_class is correct.
    manager = BaseManager()
    assert isinstance(manager, BaseManager)
    assert isinstance(manager._queryset_class, type)
    assert manager._queryset_class == BaseQuerySet

def test_manager_uses_base_queryset():
    # Test that the manager's get_queryset method returns an instance of BaseQuerySet
    class MyConcreteModel(AbstractModel):
        class Meta:
            app_label = 'hope_documents'
            managed = False # Don't try to create table in DB for this test model

    manager = MyConcreteModel.objects
    assert isinstance(manager.all(), BaseQuerySet)


def test_meta_options():
    assert AbstractModel._meta.abstract
    assert AbstractModel._meta.app_label == "hope_documents"

def test_last_modify_date_field():
    field = AbstractModel._meta.get_field("last_modify_date")
    assert isinstance(field, models.DateTimeField)
    assert field.auto_now

def test_manager_inheritance_on_concrete_model():
    # Test that a concrete model inheriting from AbstractModel gets BaseManager
    class MyConcreteModel(AbstractModel):
        name = models.CharField(max_length=255)
        class Meta:
            app_label = 'hope_documents'
            managed = False # Prevent Django from trying to create a DB table

    assert isinstance(MyConcreteModel.objects, BaseManager)
    assert hasattr(MyConcreteModel.objects, '_queryset_class')
    assert MyConcreteModel.objects._queryset_class == BaseQuerySet
