import factory.fuzzy
import pycountry

from hope_documents.archive.models import Country, DocumentRule, DocumentType

from .base import AutoRegisterModelFactory

all_countries = list(pycountry.countries)


class CountryFactory(AutoRegisterModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("code2",)

    class Params:
        country_data = factory.Iterator(all_countries)

    name = factory.LazyAttribute(lambda o: o.country_data.name)
    code2 = factory.LazyAttribute(lambda o: o.country_data.alpha_2)
    code3 = factory.LazyAttribute(lambda o: o.country_data.alpha_3)
    number = factory.LazyAttribute(lambda o: o.country_data.numeric)


class DocumentTypeFactory(AutoRegisterModelFactory):
    class Meta:
        model = DocumentType
        django_get_or_create = ("code",)

    code = factory.Iterator(["ID", "DL", "PAS", "ED"])
    name = factory.Iterator(["ID", "Driver License", "Passport", "Electoral Card"])


class DocumentRuleFactory(AutoRegisterModelFactory):
    class Meta:
        model = DocumentRule
        django_get_or_create = ("country", "type")

    country = factory.SubFactory(CountryFactory)
    type = factory.SubFactory(DocumentTypeFactory)
    match_regex = ".*"
    number_regex = ".*"
