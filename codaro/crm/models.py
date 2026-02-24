from django.db import models
from django.contrib.auth.models import User


class Country(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class LeadSource(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    lead_source = models.ForeignKey(LeadSource, on_delete=models.CASCADE, blank=True, null=True)
    lead_owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    vat_number = models.CharField(max_length=255)

    def __str__(self):
        return self.name
