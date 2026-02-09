# datetime is used for getting "today's date" and converting strings like "14:30" into time objects
from datetime import datetime
import os

# Flask tools for routing, templates, user input, redirects, and messages
from flask import Flask, render_template, request, redirect, url_for, flash

# Import specific functions from "controllers" file to handle data
from controllers import (
    add_entry,
    get_today_totals,
    get_today_entries,
    get_sugar_limit,
    set_sugar_limit,
    delete_all_today_entries,
    get_daily_totals,
    get_insulin_effect_per_unit,
    set_insulin_effect_per_unit,  # <-- make sure this exists in controllers.py
)

# Import the Entry data structure from your "models" file
from models import Entry

# Initialize the web application
app = Flask(__name__)

# Secret key is like a password used to secure "flash" messages (pop-up alerts)
# (Better practice: store in env var, but this is fine for a school IA project)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "mariam-secret-key")


@app.errorhandler(Exception)
def show_error(e):
    """
    If anything crashes, log the full traceback in Render logs.
    On Render we show a simple message; locally we show the error text.
    """
    app.logger.exception("Unhandled exception:")
    if os.environ.get("RENDER"):
        return "Internal error. Check Render logs.", 500
    return f"Error: {e}", 500


def _to_float(value: str) -> float:
    """Safely converts text input from a form into a decimal number."""
    value = (value or "").strip()
    if value == "":
        return 0.0  # If the user left it blank, treat it as zero
    return float(value)


def _parse_time(time_str: str) -> datetime | None:
    """Takes a time like '14:30' and turns it into a full date/time object for today."""
    time_str = (time_str or "").strip()
    if not time_str:
        return None

    try:
        today = datetime.now()
        # Turn the string "HH:MM" into a time object
        t = datetime.strptime(time_str, "%H:%M").time()
        # Combine today's date with the time the user typed in
        return datetime(today.year, today.month, today.day, t.hour, t.minute)
    except Exception:
        # If the user typed the time wrong, show an error message
        raise ValueError("Time must be in HH:MM format (example: 14:30)")


@app.route("/history")
def history():
    """The page that shows past sugar/water intake over time."""
    period = request.args.get("period", "week").lower()
    days = {"week": 7, "month": 30, "year": 365}.get(period, 7)

    limit = get_sugar_limit()
    daily = get_daily_totals(days)

    return render_template(
        "history.html",
        period=period,
        limit=limit,
        daily=daily,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    """Home page: form + today totals."""
    if request.method == "POST":
        try:
            # 1) Food is required
            food = request.form.get("food", "").strip()
            if not food:
                raise ValueError("Food name is required")

            # 2) Numbers (blank = 0)
            sugar = _to_float(request.form.get("sugar", "0"))
            water = _to_float(request.form.get("water", "0"))
            insulin = _to_float(request.form.get("insulin", "0"))

                        # 3) Time eaten (required)
            time_eaten_str = request.form.get("time_eaten", "").strip()
            if not time_eaten_str:
                raise ValueError("Please enter the time (HH:MM).")

            time_eaten = _parse_time(time_eaten_str)

            # 4) Adjusted sugar
            effect = get_insulin_effect_per_unit()
            adjusted_sugar = max(0.0, sugar - (insulin * effect))

            # 5) Create Entry object (make sure models.py uses water_litre!)
            entry = Entry(
                ts=datetime.now(),
                food=food,
                sugar_g=sugar,
                water_litre=water,
                insulin_units=insulin,
                time_eaten=time_eaten,
                adjusted_sugar_g=adjusted_sugar,
            )

            # 6) Save to DB
            add_entry(entry)
            flash("Entry saved successfully!")
            return redirect(url_for("index"))

        except ValueError as e:
            flash(str(e))

    totals = get_today_totals()
    totals["sugar_g"] = round(totals["sugar_g"], 1)
    totals["water_litre"] = round(totals["water_litre"], 1)
    totals["insulin_units"] = round(totals["insulin_units"], 1)

    limit = round(get_sugar_limit(), 1)
    return render_template("index.html", totals=totals, limit=limit)


@app.route("/reset_today", methods=["POST"])
def reset_today():
    """Wipes out all of today's logs to start over."""
    delete_all_today_entries()
    flash("All today's entries have been deleted.")
    return redirect(url_for("entries"))


@app.route("/entries")
def entries():
    """A simple page listing every individual thing logged today."""
    rows = get_today_entries()
    return render_template("entries.html", entries=rows)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Update daily sugar limit + insulin effect per unit."""
    if request.method == "POST":
        try:
            new_limit = float(request.form.get("limit", "0"))
            new_effect = float(request.form.get("effect_per_unit", "0"))

            if new_limit <= 0:
                raise ValueError("Limit must be > 0")
            if new_effect < 0:
                raise ValueError("Insulin effect per unit must be >= 0")

            set_sugar_limit(new_limit)
            set_insulin_effect_per_unit(new_effect)

            flash("Settings updated.")
            return redirect(url_for("settings"))

        except ValueError as e:
            flash(str(e))

    current_limit = get_sugar_limit()
    current_effect = get_insulin_effect_per_unit()
    return render_template("settings.html", limit=current_limit, effect=current_effect)
@app.route("/favicon.ico")
def favicon():
    return "", 204

# Start the app locally (Gunicorn will run it on Render)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
