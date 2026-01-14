# datetime is used for getting "today's date" and converting strings like "14:30" into time objects
from datetime import datetime
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
)
# Import the Entry data structure from your "models" file
from models import Entry

# Initialize the web application
app = Flask(__name__)
# Secret key is like a password used to secure "flash" messages (pop-up alerts)
app.secret_key = "mariam-secret-key"  


def _to_float(value: str) -> float:
    """Safely converts text input from a form into a decimal number."""
    value = (value or "").strip()
    if value == "":
        return 0.0 # If the user left it blank, treat it as zero
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
        return datetime(
            today.year,
            today.month,
            today.day,
            t.hour,
            t.minute,
            today.second,
            today.microsecond,
        )
    except Exception:
        # If the user typed the time wrong, show an error message
        raise ValueError("Time must be in HH:MM format (example: 14:30)")


@app.route("/history")
def history():
    """The page that shows past sugar/water intake over time."""
    # Look at the URL to see if the user wants to see a 'week', 'month', or 'year'
    period = request.args.get("period", "week").lower()
    # Convert those words into actual numbers of days
    days = {"week": 7, "month": 30, "year": 365}.get(period, 7)

    limit = get_sugar_limit() # Get the user's set sugar goal
    daily = get_daily_totals(days) # Pull the data for those days

    # Send all this info to the "history.html" webpage template
    return render_template(
        "history.html",
        period=period,
        limit=limit,
        daily=daily,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    """The main home page where you can add new food/drink entries."""
    # If the user just clicked "Submit" on the form (POST method)
    if request.method == "POST":
        try:
            # 1. Grab the food name and make sure it's not empty
            food = request.form.get("food", "").strip()
            if not food:
                raise ValueError("Food name is required")

            # 2. Get the numbers for sugar, water, and insulin
            sugar = _to_float(request.form.get("sugar", "0"))
            water = _to_float(request.form.get("water", "0"))
            insulin = _to_float(request.form.get("insulin", "0"))

            # 3. Handle the time: use what they typed or use 'right now'
            time_eaten_str = request.form.get("time_eaten", "")
            time_eaten = _parse_time(time_eaten_str) or datetime.now()

            # 4. Calculate 'adjusted sugar' by subtracting the insulin's effect
            effect = get_insulin_effect_per_unit()
            adjusted_sugar = max(0.0, sugar - (insulin * effect))

            # 5. Pack all this info into a single 'Entry' object
            entry = Entry(
                ts=datetime.now(),
                food=food,
                sugar_g=sugar,
                water_litre=water,
                insulin_units=insulin,
                time_eaten=time_eaten,
                adjusted_sugar_g=adjusted_sugar,
            )

            # 6. Save the entry to the database and tell the user it worked
            add_entry(entry)
            flash("Entry saved successfully!")
            return redirect(url_for("index"))

        except ValueError as e:
            # If any of the steps above failed, show the error message
            flash(str(e))

    # If the user is just visiting the page (GET method), show today's totals
    totals = get_today_totals()
    limit = get_sugar_limit()
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
    """The page where you can update your daily sugar limit goal."""
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


# Start the app in "debug mode" (makes it easier to find errors during development)
if __name__ == "__main__":
    app.run(debug=True)
