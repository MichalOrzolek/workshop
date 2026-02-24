from datetime import timedelta, date, datetime
import random
from dateutil.relativedelta import relativedelta

from django.shortcuts import render
from django.db.models import Count
from django.db.models.functions import TruncMonth, ExtractYear
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Report, ReportSource, RescueTeam


def home(request):
    today = timezone.localdate()

    # KPI (do top cards)
    kpis = {
        "total_reports": Report.objects.count(),
        "total_countries": RescueTeam.objects.count(),
        "total_sources": ReportSource.objects.count(),
        "without_owner": Report.objects.filter(dispatcher__isnull=True).count(),
        "without_source": Report.objects.filter(report_source__isnull=True).count(),
    }

    # 12 miesięcy wstecz (łącznie z bieżącym)
    months_back = 11
    start_month = (today.replace(day=1) - relativedelta(months=months_back))

    # lista pierwszych dni kolejnych miesięcy
    month_list = [
        (start_month + relativedelta(months=i))
        for i in range(months_back + 1)
    ]

    month_labels = [m.strftime("%m.%y") for m in month_list]

    recent_qs = (
        Report.objects
        .filter(created_at__date__gte=start_month, created_at__date__lte=today)
        .annotate(month=TruncMonth("created_at"))
        .values("report_source__name", "month")
        .annotate(total=Count("id"))
        .order_by()
    )

    counts_map = {}  # (source_name, month) -> total
    sources_set = set()

    for row in recent_qs:
        source = row["report_source__name"] or "No data"
        month = row["month"].date().replace(day=1)
        sources_set.add(source)
        counts_map[(source, month)] = row["total"]

    sources = sorted([s for s in sources_set if s != "No data"])
    if "No data" in sources_set:
        sources.append("No data")

    heatmap_rows = []
    for source in sources:
        heatmap_rows.append(
            {
                "source": source,
                "counts": [counts_map.get((source, m), 0) for m in month_list],
            }
        )

    # Pie: klienci wg źródła leadów
    source_qs = (
        Report.objects.values("report_source__name")
        .annotate(total=Count("id"))
        .order_by()
    )
    source_labels = []
    source_data = []
    for row in source_qs:
        source_labels.append(row["report_source__name"] or "No data")
        source_data.append(row["total"])

    # Donut: klienci wg krajów (Top N + "Other")
    top_n_countries = 6
    top_countries = list(
        Report.objects.values("rescue_team__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:top_n_countries]
    )
    top_countries_sum = sum(r["total"] for r in top_countries)
    other_countries_total = max(kpis["total_reports"] - top_countries_sum, 0)

    rescue_team_labels = [r["rescue_team__name"] for r in top_countries]
    rescue_team_data = [r["total"] for r in top_countries]
    if other_countries_total:
        rescue_team_labels.append("Other")
        rescue_team_data.append(other_countries_total)

    # Stacked bar: klienci per rok, skumulowane po Top 3 krajach + "Other"
    years = [today.year - 2, today.year - 1, today.year]
    min_year_date = date(years[0], 1, 1)

    top3_rescue_team_rows = list(
        Report.objects.filter(created_at__date__gte=min_year_date)
        .values("rescue_team_id", "rescue_team__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:3]
    )
    top3_ids = [r["rescue_team_id"] for r in top3_rescue_team_rows]
    top3_labels = {r["rescue_team_id"]: r["rescue_team__name"] for r in top3_rescue_team_rows}

    # łączna liczba klientów per rok (wszystkie kraje)
    totals_per_year = {y: 0 for y in years}
    totals_qs = (
        Report.objects.filter(created_at__date__gte=min_year_date)
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
        Report.objects.filter(created_at__date__gte=min_year_date, rescue_team_id__in=top3_ids)
        .annotate(year=ExtractYear("created_at"))
        .values("year", "rescue_team_id")
        .annotate(total=Count("id"))
        .order_by()
    )
    for row in top_year_qs:
        y = row["year"]
        cid = row["rescue_team_id"]
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
        stacked_datasets.append({"label": "Other", "data": others_per_year})

    # HBar: top właściciele leadów (liczba klientów)
    owners_qs = list(
        Report.objects.values("dispatcher__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    owner_labels = []
    owner_data = []
    for row in owners_qs:
        if row["dispatcher__name"] is None:
            label = "Brak właściciela"
        else:
            full = row["dispatcher__name"]
            label = full or row["dispatcher__name"]
        owner_labels.append(label)
        owner_data.append(row["total"])

    # tabela: ostatnio dodani klienci
    latest_Reports = (
        Report.objects.select_related("rescue_team", "report_source", "dispatcher")
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
        "donut_by_rescue_team": {
            "labels": rescue_team_labels,
            "data": rescue_team_data,
        },
        "hbar_by_owner": {
            "labels": owner_labels,
            "data": owner_data,
        },
    }

    # statuslist = [
    #     'New',
    #     'Ongoing',
    #     'Active',
    #     'Inactive',
    #     'Closed',
    # ]

    # for i in range(1, 101):
    #     Report.objects.create(
    #         name=f"Lead {i}",
    #         email=f"lead{i}@example.com",
    #         rescue_team=rescue_team.objects.get(id=random.randint(1, 5)),
    #         report_source=ReportSource.objects.get(id=random.randint(1, 3)),
    #         dispatcher=User.objects.get(id=random.randint(1, 3)),
    #         vat_number=f"VAT{1000 + i}",
    #         lead_status=statuslist[random.randint(0, 4)],
    #         created_at=(datetime.today() + timedelta(days=i)).isoformat() + "Z",
    #     )

    context = {
        "kpis": kpis,
        "day_labels": month_labels,
        "heatmap_rows": heatmap_rows,
        "latest_Reports": latest_Reports,
        "dashboard": dashboard,
    }
    return render(request, "crm/home.html", context)
