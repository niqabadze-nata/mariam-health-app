from datetime import datetime, date, timedelta
from supabase_client import supabase
from models import Entry


# =========================
# INSERT / CREATE
# =========================
def add_entry(entry: Entry) -> None:
    """
    Add a new health log entry into the app.
    Stores one user action (food/sugar/water/insulin/time eaten) so the app can
    calculate totals, show today's list, and build history charts.
    """
    data = {
        "ts": entry.ts.isoformat(),
        "food": entry.food,
        "sugar_g": float(entry.sugar_g or 0),
        "water_litre": float(entry.water_litre or 0),
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
    """
    Create a time filter so the app can reliably fetch only today's records
    from the database (used by totals, list, and delete functions).
    """
    d = date.today()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _range_window(days: int):
    """
    Create a date range filter for history views (e.g., last 7 days),
    so the app can compute daily totals for charts/progress tracking.
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
    """
    Produce the dashboard totals for today by fetching today's entries and
    summing values. Uses adjusted_sugar_g if available (more accurate),
    otherwise falls back to sugar_g.
    """
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
        sugar_val = r.get("adjusted_sugar_g")
        if sugar_val is None:
            sugar_val = r.get("sugar_g", 0)

        total_sugar += float(sugar_val or 0)
        total_water += float(r.get("water_litre", 0) or 0)
        total_insulin += float(r.get("insulin_units", 0) or 0)

    return {
        "sugar_g": total_sugar,
        "water_litre": total_water,
        "insulin_units": total_insulin,
    }


def get_today_entries():
    """
    Retrieve all entries made today (newest first).
    Powers the “today list” UI so the user can see what they logged,
    in reverse time order (most recent at the top).
    """
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
    """
    Delete the most recent entry from today.
    Allows an “undo last log” feature. Returns False if there is nothing
    to delete, otherwise deletes the newest entry and returns True.
    """
    entries = get_today_entries()
    if not entries:
        return False

    last_id = entries[0]["id"]
    supabase.table("entries").delete().eq("id", last_id).execute()
    return True


def delete_all_today_entries() -> bool:
    """
    Delete every entry from today.
    Provides a “clear today” feature (reset the day’s logs). Returns True
    after running the delete query.
    """
    start, end = _today_window()
    supabase.table("entries").delete().gte("ts", start).lt("ts", end).execute()
    return True


# =========================
# SETTINGS
# =========================
def get_sugar_limit() -> float:
    """
    Used for goal tracking (e.g., progress bar / warning when exceeding limit).
    Defaults to 50.0 if the setting is missing.
    """
    resp = (
        supabase.table("settings")
        .select("daily_sugar_limit")
        .eq("id", 1)
        .maybe_single()  # <-- IMPORTANT: avoids crash if the row doesn't exist
        .execute()
    )
    row = resp.data
    val = (row or {}).get("daily_sugar_limit")
    return float(val) if val is not None else 50.0


def set_sugar_limit(value: float) -> None:
    """
    Update daily sugar limit in settings.
    Uses upsert so the row is created if it doesn't exist yet.
    """
    supabase.table("settings").upsert(
        {"id": 1, "daily_sugar_limit": float(value)}
    ).execute()


def get_insulin_effect_per_unit() -> float:
    """
    Retrieve insulin effectiveness used by adjusted sugar calculation.
    Returns 0.0 if the setting is missing.
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


def set_insulin_effect_per_unit(value: float) -> None:
    """
    Update insulin effectiveness in settings.
    Uses upsert so the row is created if it doesn't exist yet.
    """
    supabase.table("settings").upsert(
        {"id": 1, "insulin_effect_per_unit": float(value)}
    ).execute()


# =========================
# HISTORY (DAILY TOTALS)
# =========================
def get_daily_totals(days: int):
    """
    Create summary data for history screens and charts by grouping all entries
    by date (YYYY-MM-DD) and summing sugar, water, and insulin for each day.
    Uses adjusted_sugar_g when available for accuracy.
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
        day = ts[:10]
        if not day:
            continue

        if day not in buckets:
            buckets[day] = {"sugar_g": 0.0, "water_litre": 0.0, "insulin_units": 0.0}

        sugar_val = r.get("adjusted_sugar_g")
        if sugar_val is None:
            sugar_val = r.get("sugar_g", 0)

        buckets[day]["sugar_g"] += float(sugar_val or 0)
        buckets[day]["water_litre"] += float(r.get("water_litre", 0) or 0)
        buckets[day]["insulin_units"] += float(r.get("insulin_units", 0) or 0)

    out = []
    for day in sorted(buckets.keys()):
        out.append({"day": day, **buckets[day]})

    return out
