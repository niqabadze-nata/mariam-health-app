from datetime import datetime, date, timedelta
from supabase_client import supabase
from models import Entry


def add_entry(entry: Entry) -> None:
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


def _today_window():
    d = date.today()
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _range_window(days: int):
    end_date = date.today() + timedelta(days=1)
    start_date = end_date - timedelta(days=days)
    start = datetime(start_date.year, start_date.month, start_date.day)
    end = datetime(end_date.year, end_date.month, end_date.day)
    return start.isoformat(), end.isoformat()


def get_today_totals():
    start, end = _today_window()
    resp = (
        supabase.table("entries")
        .select("*")
        .gte("time_eaten", start)
        .lt("time_eaten", end)
        .execute()
    )
    rows = resp.data or []

    total_sugar = total_water = total_insulin = 0.0
    for r in rows:
        sugar_val = r.get("adjusted_sugar_g")
        if sugar_val is None:
            sugar_val = r.get("sugar_g", 0)

        total_sugar += float(sugar_val or 0)
        total_water += float(r.get("water_litre", 0) or 0)
        total_insulin += float(r.get("insulin_units", 0) or 0)

    return {
        "sugar_g": round(total_sugar, 1),
        "water_litre": round(total_water, 1),
        "insulin_units": round(total_insulin, 1),
    }


def get_today_entries():
    start, end = _today_window()
    resp = (
        supabase.table("entries")
        .select("*")
        .gte("time_eaten", start)
        .lt("time_eaten", end)
        .order("time_eaten", desc=True)
        .execute()
    )
    return resp.data or []


def delete_all_today_entries() -> bool:
    start, end = _today_window()
    supabase.table("entries").delete().gte("time_eaten", start).lt("time_eaten", end).execute()
    return True


def get_sugar_limit() -> float:
    resp = supabase.table("settings").select("daily_sugar_limit").eq("id", 1).limit(1).execute()
    rows = resp.data or []
    if not rows:
        return 50.0
    return float(rows[0].get("daily_sugar_limit") or 50.0)


def get_insulin_effect_per_unit() -> float:
    resp = supabase.table("settings").select("insulin_effect_per_unit").eq("id", 1).limit(1).execute()
    rows = resp.data or []
    if not rows:
        return 0.0
    val = rows[0].get("insulin_effect_per_unit")
    return float(val) if val is not None else 0.0


def set_settings(daily_limit: float, effect_per_unit: float) -> None:
    # Always write BOTH values so daily_sugar_limit never becomes null
    supabase.table("settings").upsert(
        {
            "id": 1,
            "daily_sugar_limit": float(daily_limit),
            "insulin_effect_per_unit": float(effect_per_unit),
        }
    ).execute()


def get_daily_totals(days: int):
    start, end = _range_window(days)
    resp = (
        supabase.table("entries")
        .select("*")
        .gte("time_eaten", start)
        .lt("time_eaten", end)
        .execute()
    )
    rows = resp.data or []

    buckets = {}
    for r in rows:
        t = r.get("time_eaten") or ""
        day = t[:10]
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

    return [
        {
            "day": day,
            "sugar_g": round(vals["sugar_g"], 1),
            "water_litre": round(vals["water_litre"], 1),
            "insulin_units": round(vals["insulin_units"], 1),
        }
        for day, vals in sorted(buckets.items())
    ]
