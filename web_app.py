from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash

from controllers import (
    add_entry,
    get_today_totals,
    get_today_entries,
    get_sugar_limit,
    set_sugar_limit,
)
from models import Entry

from database import init_db


app = Flask(__name__)
app.secret_key = "mariam-secret-key"   # needed for flash messages

# Ensure DB exists on startup
init_db()


def _to_float(value: str) -> float:
    value = value.strip()
    if value == "":
        return 0.0
    return float(value)


@app.route("/", methods=["GET", "POST"])
def index():
    """Main page: add entry + show today's totals."""
    if request.method == "POST":
        try:
            food = request.form.get("food", "").strip()
            if not food:
                raise ValueError("Food name is required")

            sugar = _to_float(request.form.get("sugar", "0"))
            water = _to_float(request.form.get("water", "0"))
            insulin = _to_float(request.form.get("insulin", "0"))

            entry = Entry(
                ts=datetime.now(),
                food=food,
                sugar_g=sugar,
                water_cups=water,
                insulin_units=insulin,
            )
            add_entry(entry)
            flash("Entry saved successfully!")
            return redirect(url_for("index"))

        except ValueError as e:
            flash(str(e))

    totals = get_today_totals()
    limit = get_sugar_limit()

    return render_template("index.html", totals=totals, limit=limit)


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


if __name__ == "__main__":
    # debug=True auto reloads when you change code
    app.run(debug=True)
