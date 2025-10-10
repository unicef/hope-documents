from demo.factories.documents import CountryFactory, DocumentRuleFactory, DocumentTypeFactory


def generate_sample_data(**kwargs):
    CountryFactory.create_batch(3)
    DocumentTypeFactory.create_batch(3)
    DocumentRuleFactory(type__code="DL", country__code2="IT")
