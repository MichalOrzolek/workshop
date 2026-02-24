from django.db import models
from django.contrib.auth.models import User

from datetime import date

class Country(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Countries"


class LeadSource(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Lead Sources"


class Customer(models.Model):
    listastatus = (
        ("New", "New"),
        ("Ongoing", "Ongoing"),
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Closed", "Closed"),
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    lead_source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, blank=True, null=True)
    lead_owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    vat_number = models.CharField(max_length=255)
    lead_status = models.CharField(max_length=255, choices=listastatus, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Customers"


class Deal(models.Model):
    dealstatus = (
        ("Open", "Open"),
        ("Ongoing", "Ongoing"),
        ("Closed", "Closed"),
        ("Cancelled", "Cancelled"),
    )
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    margin = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    close_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=255, choices=dealstatus, default='Open', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.close_date:
            self.status = "Closed"
        if not self.name:
            dealid = Deal.objects.all().order_by("-id").first().id if Deal.objects.all().exists() else 0
            self.name = f"COD/{dealid + 1:03d}/{date.today().year}"
        if self.cost and self.amount:
            self.margin = self.amount - self.cost
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Deals"


class Activity(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"


class SalesActivity(models.Model):
    activitystatus = (
        ("Planned", "Planned"),
        ("In Progress", "In Progress"),
        ("Success", "Success"),
        ("Failed", "Failed"),
    )
    deal = models.ForeignKey(Deal, on_delete=models.SET_NULL, blank=True, null=True)
    type_activity = models.ForeignKey(Activity, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=255, choices=activitystatus, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_activity} - {self.date}"
