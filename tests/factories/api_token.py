import factory
from django.utils import timezone
from hope_api_auth.models import APIToken

from hope_documents.grants import Grant

from .user import UserFactory


class APITokenFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    grants = factory.LazyFunction(lambda: [g.value for g in Grant])
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = None

    class Meta:
        model = APIToken
