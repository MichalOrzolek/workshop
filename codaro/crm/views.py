from datetime import timedelta, date, datetime
import random

from django.shortcuts import render
from django.db.models import Count
from django.db.models.functions import TruncDate, ExtractYear
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Country, LeadSource, Customer


def home(request):
    today = timezone.localdate()

    # KPI (do top cards)
    kpis = {
        "total_customers": Customer.objects.count(),
        "total_countries": Country.objects.count(),
        "total_sources": LeadSource.objects.count(),
        "without_owner": Customer.objects.filter(lead_owner__isnull=True).count(),
        "without_source": Customer.objects.filter(lead_source__isnull=True).count(),
    }

    # Heatmap: ostatnie 9 dni (jak na screenie)
    days_back = 8
    start_day = today - timedelta(days=days_back)
    day_list = [start_day + timedelta(days=i) for i in range(days_back + 1)]
    day_labels = [d.strftime("%d.%m") for d in day_list]  # etykiety kolumn (np. 24.02)

    recent_qs = (
        Customer.objects.filter(created_at__date__gte=start_day, created_at__date__lte=today)
        .annotate(day=TruncDate("created_at"))
        .values("lead_source__name", "day")
        .annotate(total=Count("id"))
        .order_by()  # ważne przy values+annotate
    )

    counts_map = {}  # (source_name, day) -> total
    sources_set = set()

    for row in recent_qs:
        source = row["lead_source__name"] or "Brak źródła"
        day = row["day"]
        sources_set.add(source)
        counts_map[(source, day)] = row["total"]

    sources = sorted([s for s in sources_set if s != "Brak źródła"])
    if "Brak źródła" in sources_set:
        sources.append("Brak źródła")

    heatmap_rows = []
    for source in sources:
        heatmap_rows.append(
            {
                "source": source,
                "counts": [counts_map.get((source, d), 0) for d in day_list],
            }
        )

    # Pie: klienci wg źródła leadów
    source_qs = (
        Customer.objects.values("lead_source__name")
        .annotate(total=Count("id"))
        .order_by()
    )
    source_labels = []
    source_data = []
    for row in source_qs:
        source_labels.append(row["lead_source__name"] or "Brak źródła")
        source_data.append(row["total"])

    # Donut: klienci wg krajów (Top N + "Pozostałe")
    top_n_countries = 6
    top_countries = list(
        Customer.objects.values("country__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:top_n_countries]
    )
    top_countries_sum = sum(r["total"] for r in top_countries)
    other_countries_total = max(kpis["total_customers"] - top_countries_sum, 0)

    country_labels = [r["country__name"] for r in top_countries]
    country_data = [r["total"] for r in top_countries]
    if other_countries_total:
        country_labels.append("Pozostałe")
        country_data.append(other_countries_total)

    # Stacked bar: klienci per rok, skumulowane po Top 3 krajach + "Pozostałe"
    years = [today.year - 2, today.year - 1, today.year]
    min_year_date = date(years[0], 1, 1)

    top3_country_rows = list(
        Customer.objects.filter(created_at__date__gte=min_year_date)
        .values("country_id", "country__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:3]
    )
    top3_ids = [r["country_id"] for r in top3_country_rows]
    top3_labels = {r["country_id"]: r["country__name"] for r in top3_country_rows}

    # łączna liczba klientów per rok (wszystkie kraje)
    totals_per_year = {y: 0 for y in years}
    totals_qs = (
        Customer.objects.filter(created_at__date__gte=min_year_date)
        .annotate(year=ExtractYear("created_at"))
        .values("year")
        .annotate(total=Count("id"))
        .order_by()
    )
    for row in totals_qs:
        y = row["year"]
        if y in totals_per_year:
            totals_per_year[y] = row["total"]

    # Top3 kraje per rok
    top_per_year = {cid: {y: 0 for y in years} for cid in top3_ids}
    top_year_qs = (
        Customer.objects.filter(created_at__date__gte=min_year_date, country_id__in=top3_ids)
        .annotate(year=ExtractYear("created_at"))
        .values("year", "country_id")
        .annotate(total=Count("id"))
        .order_by()
    )
    for row in top_year_qs:
        y = row["year"]
        cid = row["country_id"]
        if y in totals_per_year and cid in top_per_year:
            top_per_year[cid][y] = row["total"]

    stacked_datasets = []
    for cid in top3_ids:
        stacked_datasets.append(
            {
                "label": top3_labels[cid],
                "data": [top_per_year[cid][y] for y in years],
            }
        )

    others_per_year = []
    for y in years:
        top_sum_y = sum(top_per_year[cid][y] for cid in top3_ids)
        others_per_year.append(max(totals_per_year[y] - top_sum_y, 0))

    if any(others_per_year):
        stacked_datasets.append({"label": "Pozostałe", "data": others_per_year})

    # HBar: top właściciele leadów (liczba klientów)
    owners_qs = list(
        Customer.objects.values("lead_owner__username", "lead_owner__first_name", "lead_owner__last_name")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    owner_labels = []
    owner_data = []
    for row in owners_qs:
        if row["lead_owner__username"] is None:
            label = "Brak właściciela"
        else:
            full = f"{row['lead_owner__first_name'] or ''} {row['lead_owner__last_name'] or ''}".strip()
            label = full or row["lead_owner__username"]
        owner_labels.append(label)
        owner_data.append(row["total"])

    # tabela: ostatnio dodani klienci
    latest_customers = (
        Customer.objects.select_related("country", "lead_source", "lead_owner")
        .order_by("-created_at")[:10]
    )

    dashboard = {
        "stacked_by_year": {
            "labels": [str(y) for y in years],
            "datasets": stacked_datasets,
        },
        "pie_by_source": {
            "labels": source_labels,
            "data": source_data,
        },
        "donut_by_country": {
            "labels": country_labels,
            "data": country_data,
        },
        "hbar_by_owner": {
            "labels": owner_labels,
            "data": owner_data,
        },
    }

    statuslist = [
        'New',
        'Ongoing',
        'Active',
        'Inactive',
        'Closed',
    ]

    # for i in range(1, 101):
    #     Customer.objects.create(
    #         name=f"Lead {i}",
    #         email=f"lead{i}@example.com",
    #         country=Country.objects.get(id=random.randint(1, 5)),
    #         lead_source=LeadSource.objects.get(id=random.randint(1, 3)),
    #         lead_owner=User.objects.get(id=random.randint(1, 3)),
    #         vat_number=f"VAT{1000 + i}",
    #         lead_status=statuslist[random.randint(0, 4)],
    #         created_at=(datetime.today() + timedelta(days=i)).isoformat() + "Z",
    #     )

    context = {
        "kpis": kpis,
        "day_labels": day_labels,
        "heatmap_rows": heatmap_rows,
        "latest_customers": latest_customers,
        "dashboard": dashboard,
    }
    return render(request, "crm/home.html", context)
