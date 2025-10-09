from django.db import models
from django_regex.fields import RegexField


class Country(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class DocumentType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class DocumentRule(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    match_regex = RegexField(default=".*")
    number_regex = RegexField(default=".*")

    def __str__(self) -> str:
        return f"{self.type.name} {self.country.name}"

    def test(self, text: str) -> bool:
        return False
