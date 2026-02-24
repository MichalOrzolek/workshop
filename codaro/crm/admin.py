from django.contrib import admin
from .models import Country, LeadSource, Customer


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
    ]
    
    search_fields = [
        "name",
    ]


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
    ]
    
    search_fields = [
        "name",
    ]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "email",
        "country",
        "lead_source",
        "lead_owner",
    ]
    
    search_fields = [
        "name",
        "email",
        "country__name",
        "lead_source__name",
        "lead_owner__username",
        "lead_owner__first_name",
        "lead_owner__last_name",
    ]

    autocomplete_fields = (
        "country",
        "lead_source",
        "lead_owner",
    )
