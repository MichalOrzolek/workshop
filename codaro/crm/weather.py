from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Literal
import os
import requests


Provider = Literal["metno", "open_meteo"]


def _to_utc_dt(when: datetime | str) -> datetime:
    """
    Accepts:
      - datetime (naive treated as UTC)
      - ISO string like '2026-02-24T14:00:00Z' or '2026-02-24 14:00:00'
    Returns aware UTC datetime.
    """
    if isinstance(when, str):
        s = when.strip().replace(" ", "T")
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    else:
        dt = when

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _round_coord(x: float) -> float:
    # MET Norway strongly prefers truncation/rounding; they mention blocking for too many decimals.
    # We'll round to 4 decimals (~11m precision), which is plenty for forecasting.
    return round(float(x), 4)


def _pick_nearest_timeseries(timeseries: list[dict], target_utc: datetime) -> dict:
    best = None
    best_abs = None
    for item in timeseries:
        t = datetime.fromisoformat(item["time"].replace("Z", "+00:00")).astimezone(timezone.utc)
        diff = abs((t - target_utc).total_seconds())
        if best is None or diff < best_abs: # type: ignore
            best, best_abs = item, diff
    return best # type: ignore


def get_weather_prediction(
    *,
    latitude: float,
    longitude: float,
    when: datetime | str,
    provider: Provider = "metno",
    timeout_s: int = 15,
) -> Dict[str, Any]:
    """
    Returns a normalized prediction payload:
      {
        "provider": "...",
        "for_time_utc": "...",
        "nearest_model_time_utc": "...",
        "temperature_c": ...,
        "wind_speed_mps": ...,
        "wind_gust_mps": ...,
        "precip_mm_next_1h": ...,
        "snowfall_mm_next_1h": ...,
        "visibility_m": ...,
        "raw": {...}  # small raw extract for debugging
      }
    """
    lat = _round_coord(latitude)
    lon = _round_coord(longitude)
    target = _to_utc_dt(when)

    if provider == "metno":
        return _metno_locationforecast(lat, lon, target, timeout_s=timeout_s)
    elif provider == "open_meteo":
        return _open_meteo_forecast(lat, lon, target, timeout_s=timeout_s)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _metno_locationforecast(lat: float, lon: float, target_utc: datetime, timeout_s: int) -> Dict[str, Any]:
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    # MET Norway requires an identifying User-Agent with contact info. :contentReference[oaicite:2]{index=2}
    ua = os.getenv("METNO_USER_AGENT") or "MountainRescueApp/1.0 yourdomain.example contact@yourdomain.example"

    r = requests.get(
        url,
        params={"lat": lat, "lon": lon},
        headers={"User-Agent": ua, "Accept": "application/json"},
        timeout=timeout_s,
    )
    r.raise_for_status()
    data = r.json()

    ts = data["properties"]["timeseries"]
    nearest = _pick_nearest_timeseries(ts, target_utc)
    nearest_time = datetime.fromisoformat(nearest["time"].replace("Z", "+00:00")).astimezone(timezone.utc)

    instant = nearest["data"]["instant"]["details"]
    next1 = (nearest["data"].get("next_1_hours") or {}).get("details") or {}

    # Many useful fields exist; these are commonly present in compact responses.
    return {
        "provider": "metno",
        "for_time_utc": target_utc.isoformat(),
        "nearest_model_time_utc": nearest_time.isoformat(),
        "temperature_c": instant.get("air_temperature"),
        "wind_speed_mps": instant.get("wind_speed"),
        "wind_gust_mps": instant.get("wind_speed_of_gust"),
        "precip_mm_next_1h": next1.get("precipitation_amount"),
        "snowfall_mm_next_1h": next1.get("snowfall_amount"),
        "visibility_m": instant.get("visibility"),
        "raw": {
            "lat": lat,
            "lon": lon,
            "instant": {k: instant.get(k) for k in [
                "air_temperature", "wind_speed", "wind_speed_of_gust", "visibility",
                "relative_humidity", "air_pressure_at_sea_level", "cloud_area_fraction"
            ] if k in instant},
            "next_1_hours": next1,
        },
    }


def _open_meteo_forecast(lat: float, lon: float, target_utc: datetime, timeout_s: int) -> Dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast"

    # request a small hourly window around the target date (UTC)
    d0 = target_utc.date()
    start = (d0).isoformat()
    end = (d0).isoformat()

    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "UTC",
        "start_date": start,
        "end_date": end,
        "hourly": ",".join([
            "temperature_2m",
            "precipitation",
            "snowfall",
            "windspeed_10m",
            "windgusts_10m",
            "visibility",
            "weathercode",
        ]),
    }

    r = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    times = data["hourly"]["time"]  # ISO strings
    # find nearest hour
    best_i = 0
    best_abs = None
    for i, t in enumerate(times):
        dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        diff = abs((dt - target_utc).total_seconds())
        if best_abs is None or diff < best_abs:
            best_abs = diff
            best_i = i

    nearest_time = datetime.fromisoformat(times[best_i]).replace(tzinfo=timezone.utc)

    return {
        "provider": "open_meteo",
        "Time": target_utc.isoformat(),
        "Nearest time model": nearest_time.isoformat(),
        "Temperature (C)": data["hourly"]["temperature_2m"][best_i],
        "Wind speed km/h": data["hourly"]["windspeed_10m"][best_i],
        "Wind gusts km/h": data["hourly"]["windgusts_10m"][best_i],
        "Precipitation mm: next 1h": data["hourly"]["precipitation"][best_i],
        "Snowfall mm: next 1h": data["hourly"]["snowfall"][best_i],
        "Visibility m": data["hourly"]["visibility"][best_i],
        "raw": {
            "lat": lat,
            "lon": lon,
            "weathercode": data["hourly"]["weathercode"][best_i],
        },
    }




# extend the code here:
def _escape_html(x) -> str:
    s = "" if x is None else str(x)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )

def prediction_to_html_table(pred: dict) -> str:
    """
    Convert the prediction dict to a simple HTML table.
    Nested dicts (like pred['raw']) are flattened into separate rows with key prefix.
    """
    rows = []

    def add_row(k: str, v):
        rows.append(
            f"<tr><th style='text-align:left;padding:6px;border:1px solid #ddd;'>{_escape_html(k)}</th>"
            f"<td style='padding:6px;border:1px solid #ddd'>{_escape_html(v)}</td></tr>"
        )

    for key, value in pred.items():
        if isinstance(value, dict):
            for k2, v2 in value.items():
                add_row(f"{key}.{k2}", v2)
        else:
            add_row(key, value)

    html = (
        "<table style='border-collapse:collapse;min-width:520px'>"
        + "".join(rows) +
        "</table>"
    )
    return html
