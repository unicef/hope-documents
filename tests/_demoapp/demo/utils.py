def generate_sample_data(**kwargs):
    from demo.factories.documents import CountryFactory, DocumentRuleFactory, DocumentTypeFactory

    CountryFactory.create_batch(6)
    DocumentTypeFactory.create_batch(4)
    DocumentRuleFactory(type__code="DL", country__code2="IT")
