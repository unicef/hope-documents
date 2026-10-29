from typing import Any

from django.core.management import BaseCommand

from hope_documents.archive.models import Attribute, Country, Document, DocumentAttribute, DocumentType


class Command(BaseCommand):
    help = "Create demo documents, attributes, and regions for manual testing"

    def _seed_country(self) -> Country:
        ita, created = Country.objects.get_or_create(
            code2="IT",
            defaults={"code3": "ITA", "number": "380", "name": "Italy", "full_name": "Italian Republic"},
        )
        if created:
            self.stdout.write(f"  Created country: {ita}")
        return ita

    def _seed_document_types(self) -> tuple[DocumentType, DocumentType]:
        dl, created = DocumentType.objects.get_or_create(
            code="DL",
            defaults={"name": "Driver License", "description": "National driving licence"},
        )
        if created:
            self.stdout.write(f"  Created document type: {dl}")
        pas, created = DocumentType.objects.get_or_create(
            code="PAS",
            defaults={"name": "Passport", "description": "National/international passport"},
        )
        if created:
            self.stdout.write(f"  Created document type: {pas}")
        return dl, pas

    def _seed_document_attributes(self, doc: Document, attrs: list[tuple[Attribute, str | None]]) -> None:
        for attr, expr in attrs:
            obj, created = DocumentAttribute.objects.get_or_create(
                document=doc,
                attribute=attr,
                defaults={"validation_expression": expr},
            )
            if created:
                self.stdout.write(f"  Created attribute: {obj}")

    def handle(self, *args: Any, **options: Any) -> None:
        ita = self._seed_country()
        dl_type, pas_type = self._seed_document_types()

        dl_doc, created = Document.objects.get_or_create(document_type=dl_type, country=ita, version="2024")
        if created:
            self.stdout.write(f"  Created document: {dl_doc}")

        pas_doc, created = Document.objects.get_or_create(document_type=pas_type, country=ita, version="2024")
        if created:
            self.stdout.write(f"  Created document: {pas_doc}")

        system_attrs = {a.name: a for a in Attribute.objects.filter(system=True)}
        missing = [n for n in ("first_name", "last_name", "document_number") if n not in system_attrs]
        if missing:
            self.stdout.write(self.style.ERROR(f"Missing system attributes: {missing}. Run 'manage.py migrate' first."))
            return

        first_name = system_attrs["first_name"]
        last_name = system_attrs["last_name"]
        doc_number = system_attrs["document_number"]

        self._seed_document_attributes(
            dl_doc,
            [
                (first_name, None),
                (last_name, None),
                (doc_number, r"[A-Z]{2}\d{7}[A-Z]"),
            ],
        )
        self._seed_document_attributes(
            pas_doc,
            [
                (first_name, None),
                (last_name, None),
                (doc_number, r"[A-Z]{2}\d{7}"),
            ],
        )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
