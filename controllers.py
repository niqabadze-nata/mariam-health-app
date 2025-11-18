from datetime import datetime, date, timedelta
from supabase_client import supabase
from models import Entry


def add_entry(entry: Entry):
    """Insert one entry into Supabase."""
    data = {
        "ts": entry.ts.isoformat(),
        "food": entry.food,
        "sugar_g": entry.sugar_g,
        "water_cups": entry.water_cups,
        "insulin_units": entry.insulin_units,
    }
    supabase.table("entries").insert(data).execute()


def _today_window():
    """Return start/end ISO timestamps for today."""
    d = date.today()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def get_today_totals():
    """Calculate today totals by summing values from Supabase."""
    start, end = _today_window()
    resp = (
        supabase.table("entries")
        .select("*")
        .gte("ts", start)
        .lt("ts", end)
        .execute()
    )
    rows = resp.data or []

    total_sugar = sum(r["sugar_g"] for r in rows)
    total_water = sum(r["water_cups"] for r in rows)
    total_insulin = sum(r["insulin_units"] for r in rows)

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
    resp = (
        supabase.table("entries")
        .delete()
        .gte("ts", start)
        .lt("ts", end)
        .execute()
    )
    return True
