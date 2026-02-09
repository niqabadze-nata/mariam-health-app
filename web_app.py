import re
from datetime import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.exceptions import HTTPException

# ... your imports stay the same ...


def _to_float_field(value: str, field_name: str) -> float:
    """
    Converts a form value to float.
    - Allows blank -> 0.0
    - Allows comma decimals (2,5)
    - Raises a nice error if invalid (e.g. 'abc')
    """
    raw = (value or "").strip()
    if raw == "":
        return 0.0

    raw = raw.replace(",", ".")  # allow 2,5
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{field_name} must be a number.")


def _validate_food(food: str) -> str:
    """
    Food must contain at least one letter.
    So '123' is invalid, but 'cake 2' is fine.
    """
    food = (food or "").strip()
    if not food:
        raise ValueError("Food name is required.")

    if not re.search(r"[A-Za-z]", food):
        raise ValueError("Food name cannot be only numbers. Please type a real food name.")

    return food


@app.route("/", methods=["GET", "POST"])
def index():
    """Home page: form + today totals."""
    if request.method == "POST":
        try:
            # 1) Food validation (reject numbers-only)
            food = _validate_food(request.form.get("food", ""))

            # 2) Numbers (blank = 0, invalid = error message)
            sugar = _to_float_field(request.form.get("sugar", ""), "Sugar (g)")
            water = _to_float_field(request.form.get("water", ""), "Water (litre)")
            insulin = _to_float_field(request.form.get("insulin", ""), "Insulin (units)")

            # Optional extra: prevent negative values
            if sugar < 0 or water < 0 or insulin < 0:
                raise ValueError("Numbers cannot be negative.")

            # 3) Time eaten (required)
            time_eaten_str = request.form.get("time_eaten", "").strip()
            if not time_eaten_str:
                raise ValueError("Please enter the time (HH:MM).")
            time_eaten = _parse_time(time_eaten_str)

            # 4) Adjusted sugar
            effect = get_insulin_effect_per_unit()
            adjusted_sugar = max(0.0, sugar - (insulin * effect))

            # 5) Create Entry object
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
            # Accept both "2.5" and "2,5"
            raw_limit = (request.form.get("limit", "0") or "").strip().replace(",", ".")
            raw_effect = (
                (request.form.get("effect_per_unit", "0") or "").strip().replace(",", ".")
            )

            new_limit = float(raw_limit)
            new_effect = float(raw_effect)

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


# Start the app locally (Gunicorn will run it on Render)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
