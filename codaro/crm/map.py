from __future__ import annotations

from datetime import datetime


# ----------------------------
# Helpers
# ----------------------------
def _escape_html(x) -> str:
    s = "" if x is None else str(x)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )

def _round_coord(x: float) -> float:
    return round(float(x), 5)


# ----------------------------
# OpenStreetMap embed
# ----------------------------
def osm_iframe_html(latitude: float, longitude: float, *, zoom: int = 6, width: str = "100%", height_px: int = 420) -> str:
    """
    Returns an OpenStreetMap <iframe> embed centered on lat/lon with a marker.

    Uses openstreetmap.org embed (public). No key required.
    """
    lat = _round_coord(latitude)
    lon = _round_coord(longitude)

    # Build a small bounding box around the point to satisfy OSM embed bbox param
    # bbox = left,bottom,right,top
    delta = 0.02  # ~2km-ish in latitude
    left = lon - delta
    right = lon + delta
    bottom = lat - delta
    top = lat + delta

    src = (
        "https://www.openstreetmap.org/export/embed.html"
        f"?bbox={left:.5f}%2C{bottom:.5f}%2C{right:.5f}%2C{top:.5f}"
        f"&layer=mapnik&marker={lat:.5f}%2C{lon:.5f}"
    )

    # Also include a "View larger map" link
    link = f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lon:.5f}#map={zoom}/{lat:.5f}/{lon:.5f}"

    return (
        "<h3 style='margin:18px 0 10px 0'>Map (OpenStreetMap)</h3>"
        f"<div style='border:1px solid #e5e7eb;border-radius:10px;overflow:hidden'>"
        f"<iframe "
        f"width='{_escape_html(width)}' height='{int(height_px)}' "
        f"frameborder='0' scrolling='no' marginheight='0' marginwidth='0' "
        f"src='{src}'></iframe>"
        f"</div>"
        f"<div style='margin-top:8px'>"
        f"<a href='{link}' target='_blank' rel='noopener noreferrer'>View larger map</a>"
        f"</div>"
    )


# ----------------------------
# One-call HTML block (table + map)
# ----------------------------
def generate_rescue_briefing_html(
    *,
    latitude: float,
    longitude: float,
    when: datetime | str,
    zoom: int = 6,
    timeout_s: int = 15,
) -> str:
    """
    Returns a full HTML snippet you can inject into your admin panel or any page.
    Includes:
      - Weather prediction as HTML table
      - OSM map embed
    """

    map_html = osm_iframe_html(latitude, longitude, zoom=zoom)

    # wrapper makes it easy to inject below any existing content
    return (
        "<div style='font-family:Arial, sans-serif'>"
        + map_html +
        "</div>"
    )
