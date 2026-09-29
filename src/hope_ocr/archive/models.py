from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import ProtectedError
from django.utils.translation import gettext as _
from django_regex.fields import RegexField


class Country(models.Model):
    name = models.CharField(max_length=255)
    code2 = models.CharField(max_length=2, validators=[RegexValidator("^[A-Z]{2}$")], unique=True)
    code3 = models.CharField(max_length=3, validators=[RegexValidator("^[A-Z]{3}$")], unique=True)
    number = models.CharField(max_length=3, validators=[RegexValidator("^[0-9]{3}$")], unique=True)
    full_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("full_name"),
        help_text=_("Official full name of the country."),
    )
    iso_code2 = models.CharField(
        max_length=2,
        blank=True,
        verbose_name=_("iso_code2"),
        help_text=_("Supplementary ISO 3166-1 alpha-2 two-letter code."),
    )
    iso_code3 = models.CharField(
        max_length=3,
        blank=True,
        verbose_name=_("iso_code3"),
        help_text=_("Supplementary ISO 3166-1 alpha-3 three-letter code."),
    )
    un_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("un_code"),
        help_text=_("Supplementary UN/numeric country code."),
    )

    class Meta:
        verbose_name_plural = _("Countries")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class DocumentType(models.Model):
    code = models.CharField(max_length=4, validators=[RegexValidator("^[A-Z]{3,4}$")], unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_("Optional human-readable description of this document type."),
    )

    class Meta:
        verbose_name_plural = _("Document Types")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Attribute(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("name"),
        help_text=_("Unique identifier for this extractable field."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_("Human-readable description of what this attribute represents."),
    )
    system = models.BooleanField(
        default=False,
        verbose_name=_("system"),
        help_text=_("Built-in system attributes (first_name, last_name, number) cannot be renamed or deleted."),
    )

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.pk and self.system:
            original = Attribute.objects.get(pk=self.pk)
            if original.name != self.name:
                raise ValidationError({"name": _("System attribute names cannot be changed.")})

    def delete(self, using: str | None = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        if self.system:
            raise ProtectedError(_("System attributes cannot be deleted."), [self])
        return super().delete(using=using, keep_parents=keep_parents)


class Document(models.Model):
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE,
        verbose_name=_("document_type"),
        help_text=_("The type of document this configuration applies to."),
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name=_("country"),
        help_text=_("The country this document configuration applies to."),
    )
    version = models.CharField(
        max_length=255,
        verbose_name=_("version"),
        help_text=_(
            "Free-text version label grouping the attribute set for this document type and country. "
            "Can be a year (e.g. '2019') or an iteration label (e.g. 'v2')."
        ),
    )

    class Meta:
        ordering = ("document_type__name", "country__name", "version")
        unique_together = [("document_type", "country", "version")]

    def __str__(self) -> str:
        return f"{self.document_type} — {self.country} v{self.version}"


class DocumentAttribute(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        verbose_name=_("document"),
        help_text=_("The document configuration this attribute belongs to."),
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        verbose_name=_("attribute"),
        help_text=_("The extractable field from the Attributes catalog."),
    )
    region = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("region"),
        help_text=_('Bounding box, e.g. {"x": 10, "y": 20, "width": 100, "height": 50}'),
    )

    class Meta:
        ordering = ("document", "attribute__name")
        unique_together = [("document", "attribute")]

    def __str__(self) -> str:
        return f"{self.document} — {self.attribute}"


class DocumentRule(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    match_regex = RegexField(default=".*")
    number_regex = RegexField(default=".*")

    class Meta:
        verbose_name_plural = _("Document Rules")
        ordering = ("country__name", "type__name")

    def __str__(self) -> str:
        return f"{self.type.name} {self.country.name}"
