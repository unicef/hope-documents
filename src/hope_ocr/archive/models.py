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
    full_name = models.CharField(max_length=255, blank=True)
    iso_code2 = models.CharField(max_length=2, blank=True)
    iso_code3 = models.CharField(max_length=3, blank=True)
    un_code = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name_plural = _("Countries")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class DocumentType(models.Model):
    code = models.CharField(max_length=4, validators=[RegexValidator("^[A-Z]{3,4}$")], unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = _("Document Types")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Attribute(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    system = models.BooleanField(default=False)

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
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    version = models.CharField(max_length=255)

    class Meta:
        ordering = ("document_type__name", "country__name", "version")
        unique_together = [("document_type", "country", "version")]

    def __str__(self) -> str:
        return f"{self.document_type} — {self.country} v{self.version}"


class DocumentAttribute(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    region = models.JSONField(
        null=True,
        blank=True,
        help_text='Bounding box, e.g. {"x": 10, "y": 20, "width": 100, "height": 50}',
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
