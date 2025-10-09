from factory.django import DjangoModelFactory

from .base import AutoRegisterModelFactory, TAutoRegisterModelFactory, factories_registry
from .user import GroupFactory, SuperUserFactory, User, UserFactory  # noqa

django_model_factories = {factory._meta.model: factory for factory in DjangoModelFactory.__subclasses__()}


def get_factory_for_model(
    _model,
) -> type[TAutoRegisterModelFactory] | type[DjangoModelFactory]:
    class Meta:
        model = _model

    bases = (AutoRegisterModelFactory,)
    if _model in factories_registry:
        return factories_registry[_model]

    if _model in django_model_factories:
        return django_model_factories[_model]

    return type(f"{_model._meta.model_name}AutoCreatedFactory", bases, {"Meta": Meta})
