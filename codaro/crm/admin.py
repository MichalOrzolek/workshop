from django.contrib import admin
from .models import Country, LeadSource, Customer, Deal

from datetime import datetime, timedelta
import random

admin.site.site_header = "Codaro CRM Admin"
admin.site.site_title = "Codaro CRM Admin Portal"
admin.site.index_title = "Welcome to Codaro CRM Admin Portal"


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
        "created_at",
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

    actions = [
        'datechange',
    ]

    def datechange(self, request, queryset):
        for z in queryset:
            Customer.objects.filter(id=z.id).update(
                created_at=datetime.now() - timedelta(days=random.randint(1, 700)),
            )


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):  
    list_display = [
        "name",
        "customer",
        "cost",
        "amount",
        "margin",
        "close_date",
        "status",
    ]
    
    search_fields = [
        "name",
        "customer__name",
    ]

    readonly_fields = [
        "name",
        "margin",
    ]

    list_filter = [
        "status",
    ]

    autocomplete_fields = (
        "customer",
    )

    date_hierarchy = "close_date"
