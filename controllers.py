from datetime import datetime, date, timedelta

from supabase_client import supabase
from models import Entry


# =========================
# INSERT / CREATE
# =========================
def add_entry(entry: Entry) -> None:
    """Insert one entry into Supabase."""
    data = {
        "ts": entry.ts.isoformat(),
        "food": entry.food,
        "sugar_g": float(entry.sugar_g or 0),
        "water_liter": float(entry.water_liter or 0),
        "insulin_units": float(entry.insulin_units or 0),
        "adjusted_sugar_g": float(entry.adjusted_sugar_g or 0),
    }

    if getattr(entry, "time_eaten", None):
        data["time_eaten"] = entry.time_eaten.isoformat()

    supabase.table("entries").insert(data).execute()


# =========================
# DATE HELPERS
# =========================
def _today_window():
    """Return start/end ISO timestamps for today (local server time)."""
    d = date.today()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _range_window(days: int):
    """
    Returns start/end ISO timestamps for a range ending today.
    Example: days=7 -> last 7 days including today.
    """
    end_date = date.today() + timedelta(days=1)  # exclusive end
    start_date = end_date - timedelta(days=days)

    start = datetime(start_date.year, start_date.month, start_date.day)
    end = datetime(end_date.year, end_date.month, end_date.day)
    return start.isoformat(), end.isoformat()


# =========================
# TODAY: TOTALS / LIST / DELETE
# =========================
def get_today_totals():
    """Calculate today's totals by summing values from Supabase."""
    start, end = _today_window()

    resp = (
        supabase.table("entries")
        .select("*")
        .gte("ts", start)
        .lt("ts", end)
        .execute()
    )
    rows = resp.data or []

    total_sugar = 0.0
    total_water = 0.0
    total_insulin = 0.0

    for r in rows:
        # prefer adjusted_sugar_g if present, fallback to sugar_g
        sugar_val = r.get("adjusted_sugar_g")
        if sugar_val is None:
            sugar_val = r.get("sugar_g", 0)

        total_sugar += float(sugar_val or 0)
        total_water += float(r.get("water_liter", 0) or 0)
        total_insulin += float(r.get("insulin_units", 0) or 0)

    return {
        "sugar_g": total_sugar,
        "water_liter": total_water,
        "insulin_units": total_insulin,
    }


def get_today_entries():
    """Return all entries for today (most recent first)."""
    start, end = _today_window()

    resp = (
        supabase.table("entries")
        .select("*")
        .gte("ts", start)
        .lt("ts", end)
        .order("ts", desc=True)
        .execute()
    )
    return resp.data or []


def delete_last_today_entry() -> bool:
    """Delete the most recent entry for today."""
    entries = get_today_entries()
    if not entries:
        return False

    last_id = entries[0]["id"]
    supabase.table("entries").delete().eq("id", last_id).execute()
    return True


def delete_all_today_entries() -> bool:
    """Delete all today's entries."""
    start, end = _today_window()
    supabase.table("entries").delete().gte("ts", start).lt("ts", end).execute()
    return True


# =========================
# SETTINGS
# =========================
def get_sugar_limit() -> float:
    """Return daily sugar limit from settings (row with id=1)."""
    resp = (
        supabase.table("settings")
        .select("daily_sugar_limit")
        .eq("id", 1)
        .single()
        .execute()
    )
    row = resp.data
    val = (row or {}).get("daily_sugar_limit")
    return float(val) if val is not None else 50.0


def set_sugar_limit(value: float) -> None:
    """Update daily sugar limit in settings."""
    supabase.table("settings").update({"daily_sugar_limit": float(value)}).eq("id", 1).execute()


def get_insulin_effect_per_unit() -> float:
    """
    How many grams of sugar to subtract per 1 unit insulin.
    If missing, return 0.0.
    """
    resp = (
        supabase.table("settings")
        .select("insulin_effect_per_unit")
        .eq("id", 1)
        .maybe_single()
        .execute()
    )
    row = resp.data
    val = (row or {}).get("insulin_effect_per_unit")
    return float(val) if val is not None else 0.0


# =========================
# HISTORY (DAILY TOTALS)
# =========================
def get_daily_totals(days: int):
    """
    Returns daily totals for the last N days (including today),
    grouped by date:
    [
      {"day":"2025-12-22","sugar_g":..., "water_liter":..., "insulin_units":...},
      ...
    ]
    """
    start, end = _range_window(days)

    resp = (
        supabase.table("entries")
        .select("*")
        .gte("ts", start)
        .lt("ts", end)
        .execute()
    )
    rows = resp.data or []

    buckets = {}

    for r in rows:
        ts = r.get("ts") or ""
        day = ts[:10]  # YYYY-MM-DD
        if not day:
            continue

        if day not in buckets:
            buckets[day] = {"sugar_g": 0.0, "water_liter": 0.0, "insulin_units": 0.0}

        sugar_val = r.get("adjusted_sugar_g")
        if sugar_val is None:
            sugar_val = r.get("sugar_g", 0)

        buckets[day]["sugar_g"] += float(sugar_val or 0)
        buckets[day]["water_liter"] += float(r.get("water_liter", 0) or 0)
        buckets[day]["insulin_units"] += float(r.get("insulin_units", 0) or 0)

    out = []
    for day in sorted(buckets.keys()):
        out.append({"day": day, **buckets[day]})

    return out
