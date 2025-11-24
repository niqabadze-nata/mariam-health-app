from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

from controllers import (
    add_entry,
    get_today_totals,
    get_today_entries,
    get_sugar_limit,
    set_sugar_limit,
    delete_all_today_entries, 
)
from models import Entry

app = Flask(__name__)
app.secret_key = "mariam-secret-key"   # needed for flash messages


def _to_float(value: str) -> float:
    value = value.strip()
    if value == "":
        return 0.0
    return float(value)


def _parse_time(time_str: str) -> datetime | None:
    """
    Converts the user input (HH:MM) into a datetime for today.
    Returns None if empty.
    Raises ValueError if format invalid.
    """
    time_str = time_str.strip()
    if not time_str:
        return None

    try:
        today = datetime.now()
        t = datetime.strptime(time_str, "%H:%M").time()
        return datetime(
            today.year,
            today.month,
            today.day,
            t.hour,
            t.minute,
            today.second,
            today.microsecond
        )
    except Exception:
        raise ValueError("Time must be in HH:MM format (example: 14:30)")


@app.route("/", methods=["GET", "POST"])
def index():
    """Main page: add entry + show today's totals."""
    if request.method == "POST":
        try:
            # 1. Validate food
            food = request.form.get("food", "").strip()
            if not food:
                raise ValueError("Food name is required")

            # 2. Numbers
            sugar = _to_float(request.form.get("sugar", "0"))
            water = _to_float(request.form.get("water", "0"))
            insulin = _to_float(request.form.get("insulin", "0"))

            # 3. Time eaten (NEW feature)
            time_eaten_str = request.form.get("time_eaten", "")
            time_eaten = _parse_time(time_eaten_str)

            # If user did not enter time → use current time
            if time_eaten is None:
                time_eaten = datetime.now()

            # 4. Create entry object
            entry = Entry(
                ts=datetime.now(),
                food=food,
                sugar_g=sugar,
                water_cups=water,
                insulin_units=insulin,
                time_eaten=time_eaten,
            )

            # 5. Save
            add_entry(entry)
            flash("Entry saved successfully!")
            return redirect(url_for("index"))

        except ValueError as e:
            flash(str(e))

    totals = get_today_totals()
    limit = get_sugar_limit()
    return render_template("index.html", totals=totals, limit=limit)
@app.route("/reset_today", methods=["POST"])
def reset_today():
    delete_all_today_entries()
    flash("All today's entries have been deleted.")
    return redirect(url_for("entries"))


@app.route("/entries")
def entries():
    """List all entries for today."""
    rows = get_today_entries()
    return render_template("entries.html", entries=rows)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Change daily sugar limit."""
    if request.method == "POST":
        try:
            new_limit = float(request.form.get("limit", "0"))
            if new_limit <= 0:
                raise ValueError("Limit must be > 0")

            set_sugar_limit(new_limit)
            flash("Daily sugar limit updated.")
            return redirect(url_for("settings"))

        except ValueError as e:
            flash(str(e))

    current = get_sugar_limit()
    return render_template("settings.html", limit=current)

@app.route("/reset_today", methods=["POST"])
def reset_today():
    from controllers import delete_all_today_entries
    delete_all_today_entries()
    flash("Today's entries have been reset.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
