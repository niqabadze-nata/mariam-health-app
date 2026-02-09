import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.exceptions import HTTPException

from controllers import (
    add_entry,
    get_today_totals,
    get_today_entries,
    get_sugar_limit,
    get_daily_totals,
    get_insulin_effect_per_unit,
    delete_all_today_entries,
    set_settings,   # ✅ use this
)
from models import Entry

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "mariam-secret-key")


@app.errorhandler(Exception)
def show_error(e):
    app.logger.exception("Unhandled exception:")
    if isinstance(e, HTTPException):
        return e
    if os.environ.get("RENDER"):
        return "Internal error. Check Render logs.", 500
    return f"Error: {e}", 500


@app.route("/favicon.ico")
def favicon():
    return "", 204


def _to_float_field(value: str, field_name: str) -> float:
    raw = (value or "").strip()
    if raw == "":
        return 0.0
    raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{field_name} must be a number.")


def _validate_food(food: str) -> str:
    food = (food or "").strip()
    if not food:
        raise ValueError("Food name is required.")
    if not re.search(r"[A-Za-z]", food):
        raise ValueError("Food name cannot be only numbers.")
    return food


def _parse_time(time_str: str) -> datetime | None:
    time_str = (time_str or "").strip()
    if not time_str:
        return None
    try:
        today = datetime.now()
        t = datetime.strptime(time_str, "%H:%M").time()
        return datetime(today.year, today.month, today.day, t.hour, t.minute)
    except Exception:
        raise ValueError("Time must be in HH:MM format (example: 14:30)")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            food = _validate_food(request.form.get("food", ""))

            sugar = _to_float_field(request.form.get("sugar", ""), "Sugar (g)")
            water = _to_float_field(request.form.get("water", ""), "Water (litre)")
            insulin = _to_float_field(request.form.get("insulin", ""), "Insulin (units)")

            if sugar < 0 or water < 0 or insulin < 0:
                raise ValueError("Numbers cannot be negative.")

            time_eaten_str = (request.form.get("time_eaten", "") or "").strip()
            if not time_eaten_str:
                raise ValueError("Please enter the time (HH:MM).")
            time_eaten = _parse_time(time_eaten_str)

            effect = get_insulin_effect_per_unit()
            adjusted_sugar = max(0.0, sugar - (insulin * effect))

            entry = Entry(
                ts=datetime.now(),
                food=food,
                sugar_g=sugar,
                water_litre=water,
                insulin_units=insulin,
                time_eaten=time_eaten,
                adjusted_sugar_g=adjusted_sugar,
            )

            add_entry(entry)
            flash("Entry saved successfully!")
            return redirect(url_for("index"))

        except ValueError as e:
            flash(str(e))

    totals = get_today_totals()
    totals["sugar_g"] = round(totals.get("sugar_g", 0.0) or 0.0, 1)
    totals["water_litre"] = round(totals.get("water_litre", 0.0) or 0.0, 1)
    totals["insulin_units"] = round(totals.get("insulin_units", 0.0) or 0.0, 1)

    limit = round(get_sugar_limit(), 1)
    return render_template("index.html", totals=totals, limit=limit)


@app.route("/entries")
def entries():
    rows = get_today_entries()
    return render_template("entries.html", entries=rows)


@app.route("/reset_today", methods=["POST"])
def reset_today():
    delete_all_today_entries()
    flash("All today's entries have been deleted.")
    return redirect(url_for("entries"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            raw_limit = (request.form.get("limit", "") or "").strip().replace(",", ".")
            raw_effect = (request.form.get("effect_per_unit", "") or "").strip().replace(",", ".")

            new_limit = float(raw_limit)
            new_effect = float(raw_effect)

            if new_limit <= 0:
                raise ValueError("Limit must be > 0")
            if new_effect < 0:
                raise ValueError("Insulin effect per unit must be >= 0")

            # ✅ save both together so NOT NULL never breaks
            set_settings(new_limit, new_effect)

            flash("Settings updated.")
            return redirect(url_for("settings"))

        except ValueError as e:
            flash(str(e))

    current_limit = get_sugar_limit()
    current_effect = get_insulin_effect_per_unit()
    return render_template("settings.html", limit=current_limit, effect=current_effect)


@app.route("/history")
def history():
    period = request.args.get("period", "week").lower()
    days = {"week": 7, "month": 30, "year": 365}.get(period, 7)

    limit = get_sugar_limit()
    daily = get_daily_totals(days)
    return render_template("history.html", period=period, limit=limit, daily=daily)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
