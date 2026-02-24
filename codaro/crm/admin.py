from django.contrib import admin
from django.utils.safestring import mark_safe
from typing import Dict, List
from .models import Report, ReportSource, RescueTeam, Dispatcher
from .functions import rescue_status, display_seconds
from .weather import get_weather_prediction, prediction_to_html_table
from .map import generate_rescue_briefing_html
from datetime import datetime, date, timezone
from decimal import Decimal

import json
import random 

admin.site.site_header = "Codaro CRM Admin"
admin.site.site_title = "Codaro CRM Admin Portal"
admin.site.index_title = "Welcome to Codaro CRM Admin Portal"


@admin.register(RescueTeam)
class RescueTeamAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "availability",
    ]
    
    search_fields = [
        "name",
    ]

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'autocomplete' in request.path:
            if 'report' in request.headers['referer']:
                queryset = queryset.exclude(availability=False)
        return queryset, use_distinct


@admin.register(ReportSource)
class ReportSourceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
    ]
    
    search_fields = [
        "name",
    ]


@admin.register(Dispatcher)
class DispatcherAdmin(admin.ModelAdmin):
    list_display = [
        "name",
    ]
    
    search_fields = [
        "name",
    ]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    fields = [
        "report_number",
        ("lat", "lon"),
        "rescue_team",
        "report_source",
        "dispatcher",
        "report_status",
        ("created_at", "rescue_assigned_at", "closed_at"),
        'weather_table',
        'streetmap',
    ]

    list_display = [
        "report_number",
        "lat",
        "lon",
        "rescue_team",
        "report_source",
        "dispatcher",
        "report_status",
        "created_at",
        "rescue_assigned_at",
        "closed_at",
        "team_assigned",
        "from_assigned_to_closed",
        "from_report_to_closed",
    ]
    
    search_fields = [
        "report_number",
    ]

    autocomplete_fields = (
        "report_source",
        "rescue_team",
        "dispatcher",
    )

    readonly_fields = [
        'rescue_assigned_at',
        'closed_at',
        'created_at',
        'report_status',
        'report_number',
        'weather_table',
        'streetmap',
    ]

    list_filter = [
        'report_status',
    ]

    actions = [
        'success',
        'failed',
        'cancelled',
    ]

    def weather_table(self, obj):
        if obj.lat and obj.lon:
            test_lat = obj.lat
            test_lon = obj.lon
            when = datetime.now().isoformat()

            pred = get_weather_prediction(
                latitude=test_lat,
                longitude=test_lon,
                when=when,
                provider="open_meteo",
            )
            return mark_safe(prediction_to_html_table(pred))
        return '-'
    
    def streetmap(self, obj):
        if obj.lat and obj.lon:
            lat = obj.lat
            lon = obj.lon
            when = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()

            htmlapi = (
                generate_rescue_briefing_html(latitude=lat, longitude=lon, when=when, zoom=6)
            )
            map_html = f'''
            <script>
            document.currentScript.parentElement.style.width = "100%";
            </script>
            {htmlapi}
            '''
            return mark_safe(map_html)
        return '-'

    def team_assigned(self, obj):
        if obj.seconds_rescue_team_assigned < 900:
            color = '80EF80'
        elif obj.seconds_rescue_team_assigned < 1800:
            color = 'fed304'
        else:
            color = 'FF6961'
        return mark_safe(f"<span style='color:#{color};'>{display_seconds(obj.seconds_rescue_team_assigned)}</span>")

    def from_assigned_to_closed(self, obj):
        if obj.seconds_closed_from_assign:
            if obj.seconds_closed_from_assign < 18000:
                color = '80EF80'
            elif obj.seconds_closed_from_assign < 36000:
                color = 'fed304'
            else:
                color = 'FF6961'
            return mark_safe(f"<span style='color:#{color};'>{display_seconds(obj.seconds_closed_from_assign)}</span>")
        return '-'

    def from_report_to_closed(self, obj):
        if obj.seconds_closed_from_report:
            if obj.seconds_closed_from_report < 18000:
                color = '80EF80'
            elif obj.seconds_closed_from_report < 36000:
                color = 'fed304'
            else:
                color = 'FF6961'
            return mark_safe(f"<span style='color:#{color};'>{display_seconds(obj.seconds_closed_from_report)}</span>")
        return '-'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        rescue_status(obj)

    def success(self, request, queryset):
        queryset.update(closed_at=datetime.now(), report_status='Success')
        for z in queryset:
            rescue_status(z)

    def failed(self, request, queryset):
        queryset.update(closed_at=datetime.now(), report_status='Failed')
        for z in queryset:
            rescue_status(z)
        
    def cancelled(self, request, queryset):
        queryset.update(closed_at=datetime.now(), report_status='Cancelled')
        for z in queryset:
            rescue_status(z)
