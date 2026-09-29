from typing import Any

from django.db import migrations

SYSTEM_ATTRIBUTES = ("first_name", "last_name", "number")


def seed_attributes(apps: Any, schema_editor: Any) -> None:
    Attribute = apps.get_model("archive", "Attribute")
    for name in SYSTEM_ATTRIBUTES:
        Attribute.objects.get_or_create(name=name, defaults={"system": True})


def remove_attributes(apps: Any, schema_editor: Any) -> None:
    Attribute = apps.get_model("archive", "Attribute")
    Attribute.objects.filter(name__in=SYSTEM_ATTRIBUTES, system=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0003_attribute_country_full_name_country_iso_code2_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_attributes, remove_attributes),
    ]
