from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext as _
from django_regex.fields import RegexField


class Country(models.Model):
    name = models.CharField(max_length=255)
    code2 = models.CharField(max_length=2, validators=[RegexValidator("^[A-Z]{2}$")], unique=True)
    code3 = models.CharField(max_length=3, validators=[RegexValidator("^[A-Z]{3}$")], unique=True)
    number = models.CharField(max_length=3, validators=[RegexValidator("^[0-9]{3}$")], unique=True)

    class Meta:
        verbose_name_plural = _("Countries")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class DocumentType(models.Model):
    code = models.CharField(max_length=4, validators=[RegexValidator("^[A-Z]{3,4}$")], unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = _("Document Types")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


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
