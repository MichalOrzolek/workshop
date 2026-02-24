from django.db import models
from django.contrib.auth.models import User

from datetime import date, datetime


class RescueTeam(models.Model):
    name = models.CharField(max_length=255)
    availability = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Rescue teams"


class ReportSource(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Report sources"


class Dispatcher(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Dispatchers"


class Report(models.Model):
    liststatus = (
        ("New", "New"),
        ("Ongoing", "Ongoing"),
        ("Success", "Success"),
        ("Failed", "Failed"),
        ("Cancelled", "Cancelled"),
    )
    report_number = models.CharField(max_length=255)
    rescue_team = models.ForeignKey(RescueTeam, on_delete=models.SET_NULL, blank=True, null=True)
    report_source = models.ForeignKey(ReportSource, on_delete=models.SET_NULL, blank=True, null=True)
    dispatcher = models.ForeignKey(Dispatcher, on_delete=models.SET_NULL, blank=True, null=True)
    report_status = models.CharField(max_length=255, choices=liststatus, blank=True, null=True, default='New')
    created_at = models.DateTimeField(blank=True, null=True)
    rescue_assigned_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    seconds_rescue_team_assigned = models.IntegerField(blank=True, null=True)
    seconds_closed_from_assign = models.IntegerField(blank=True, null=True)
    seconds_closed_from_report = models.IntegerField(blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.now()
        if self.rescue_team and not self.rescue_assigned_at:
            self.rescue_assigned_at = datetime.now()
        if self.rescue_team and self.report_status == 'New':
            self.report_status = 'Ongoing'
        if self.report_status in ['Success', 'Failed'] and not self.closed_at:
            self.closed_at = datetime.now()
        if not self.report_number:
            reportid = Report.objects.all().order_by("-id").first().id if Report.objects.all().exists() else 0
            self.report_number = f"GOPR/{reportid + 1:03d}/{date.today().year}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.report_number

    class Meta:
        verbose_name_plural = "Reports"
