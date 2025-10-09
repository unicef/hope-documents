import factory.fuzzy

from hope_documents.archive.models import Country, DocumentRule, DocumentType

from .base import AutoRegisterModelFactory


class CountryFactory(AutoRegisterModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("code2",)

    name = factory.Iterator(["France", "Italy", "Spain"])
    code2 = factory.Iterator(["FR", "IT", "ES"])
    code3 = factory.Iterator(["FRA", "ITA", "ESP"])
    number = factory.Iterator(["250", "380", "724"])


class DocumentTypeFactory(AutoRegisterModelFactory):
    class Meta:
        model = DocumentType
        django_get_or_create = ("code",)

    code = factory.Iterator(["ID", "Driver License", "Passport"])
    name = factory.Iterator(["ID", "DL", "PAS"])


class DocumentRuleFactory(AutoRegisterModelFactory):
    class Meta:
        model = DocumentRule
        django_get_or_create = ("country", "type")

    country = factory.SubFactory(CountryFactory)
    type = factory.SubFactory(DocumentTypeFactory)
    match_regex = ".*"
    number_regex = ".*"
