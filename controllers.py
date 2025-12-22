from datetime import datetime, date, timedelta
from supabase_client import supabase
from models import Entry


def add_entry(entry: Entry):
    data = {
        "ts": entry.ts.isoformat(),
        "food": entry.food,
        "sugar_g": entry.sugar_g,
        "water_cups": entry.water_cups,
        "insulin_units": entry.insulin_units,
        "adjusted_sugar_g": entry.adjusted_sugar_g,
    }
    if getattr(entry, "time_eaten", None):
        data["time_eaten"] = entry.time_eaten.isoformat()
    supabase.table("entries").insert(data).execute()



def _today_window():
    """Return start/end ISO timestamps for today."""
    d = date.today()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


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

    total_sugar = sum(r.get("sugar_g", 0) for r in rows)
    total_water = sum(r.get("water_cups", 0) for r in rows)
    total_insulin = sum(r.get("insulin_units", 0) for r in rows)

    return {
        "sugar_g": total_sugar,
        "water_cups": total_water,
        "insulin_units": total_insulin,
    }


def get_sugar_limit():
    """Return daily sugar limit from settings (row with id=1)."""
    resp = (
        supabase.table("settings")
        .select("daily_sugar_limit")
        .eq("id", 1)
        .single()
        .execute()
    )
    row = resp.data
    return row["daily_sugar_limit"] if row else 50.0


def set_sugar_limit(value: float):
    """Update daily sugar limit in settings."""
    supabase.table("settings").update({"daily_sugar_limit": value}).eq("id", 1).execute()


def get_today_entries():
    """Return all entries for today."""
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


def delete_last_today_entry():
    """Delete the most recent entry for today."""
    entries = get_today_entries()
    if not entries:
        return False

    last_id = entries[0]["id"]
    supabase.table("entries").delete().eq("id", last_id).execute()
    return True


def delete_all_today_entries():
    """Delete all today's entries."""
    start, end = _today_window()
    supabase.table("entries").delete().gte("ts", start).lt("ts", end).execute()
    return True


def get_insulin_effect_per_unit():
    """How many grams of sugar to subtract per 1 unit insulin (project setting)."""
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

from datetime import datetime, date, timedelta

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


def get_daily_totals(days: int):
    """
    Returns daily totals for the last N days (including today),
    grouped by date: [{"day":"2025-12-22","sugar_g":..., "water_cups":..., "insulin_units":...}, ...]
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

    # group sums by YYYY-MM-DD
    buckets = {}
    for r in rows:
        day = (r["ts"] or "")[:10]  # "YYYY-MM-DD"
        if not day:
            continue
        if day not in buckets:
            buckets[day] = {"sugar_g": 0.0, "water_cups": 0.0, "insulin_units": 0.0}
        buckets[day]["sugar_g"] += float(r.get("sugar_g", 0) or 0)
        buckets[day]["water_cups"] += float(r.get("water_cups", 0) or 0)
        buckets[day]["insulin_units"] += float(r.get("insulin_units", 0) or 0)

    # return sorted list
    out = []
    for day in sorted(buckets.keys()):
        out.append({"day": day, **buckets[day]})
    return out
