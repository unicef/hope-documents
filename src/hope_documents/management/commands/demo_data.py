from typing import Any

from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Create demo documents, attributes, and regions for manual testing"

    def handle(self, *args: Any, **options: Any) -> None:
        from hope_ocr.archive.models import Attribute, Country, Document, DocumentAttribute, DocumentType

        # --- Country ---
        ita, created = Country.objects.get_or_create(
            code2="IT",
            defaults={
                "code3": "ITA",
                "number": "380",
                "name": "Italy",
                "full_name": "Italian Republic",
            },
        )
        if created:
            self.stdout.write(f"  Created country: {ita}")

        # --- Document types ---
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

        # --- Documents ---
        dl_doc, created = Document.objects.get_or_create(
            document_type=dl,
            country=ita,
            version="2024",
        )
        if created:
            self.stdout.write(f"  Created document: {dl_doc}")

        pas_doc, created = Document.objects.get_or_create(
            document_type=pas,
            country=ita,
            version="2024",
        )
        if created:
            self.stdout.write(f"  Created document: {pas_doc}")

        # --- Attributes (system ones must exist from seed migration) ---
        system_attrs = {a.name: a for a in Attribute.objects.filter(system=True)}
        missing = [n for n in ("first_name", "last_name", "document_number") if n not in system_attrs]
        if missing:
            self.stdout.write(
                self.style.ERROR(
                    f"Missing system attributes: {missing}. Run 'manage.py migrate' first."
                )
            )
            return

        first_name = system_attrs["first_name"]
        last_name = system_attrs["last_name"]
        doc_number = system_attrs["document_number"]

        # --- DocumentAttributes for Italian DL ---
        for attr, expr in [
            (first_name, None),
            (last_name, None),
            (doc_number, r"[A-Z]{2}\d{7}[A-Z]"),  # Italian DL number format
        ]:
            obj, created = DocumentAttribute.objects.get_or_create(
                document=dl_doc,
                attribute=attr,
                defaults={"validation_expression": expr},
            )
            if created:
                self.stdout.write(f"  Created attribute: {obj}")

        # --- DocumentAttributes for Italian Passport ---
        for attr, expr in [
            (first_name, None),
            (last_name, None),
            (doc_number, r"[A-Z]{2}\d{7}"),  # Italian passport number format
        ]:
            obj, created = DocumentAttribute.objects.get_or_create(
                document=pas_doc,
                attribute=attr,
                defaults={"validation_expression": expr},
            )
            if created:
                self.stdout.write(f"  Created attribute: {obj}")

        self.stdout.write(self.style.SUCCESS("Demo data ready."))