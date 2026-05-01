# INF601 - Advanced Programming in Python

# Zach Slusser

# Final Project

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("grocery", __name__, url_prefix="/grocery")


@bp.route("/", methods=("GET",))
@login_required
def index():
    """Display the current user's grocery list."""
    items = get_db().execute(
        "SELECT id, user_id, item_name, created_at"
        " FROM grocery_items"
        " WHERE user_id = ?"
        " ORDER BY created_at ASC, id ASC",
        (g.user["id"],),
    ).fetchall()
    return render_template("grocery/index.html", items=items)


@bp.route("/add", methods=("POST",))
@login_required
def add():
    """Add an item to the current user's grocery list."""
    item_name = request.form.get("item_name", "").strip()

    if not item_name:
        flash("Please enter a grocery item before adding.")
        return redirect(url_for("grocery.index"))

    db = get_db()
    db.execute(
        "INSERT INTO grocery_items (user_id, item_name, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (g.user["id"], item_name),
    )
    db.commit()
    flash(f"Added '{item_name}' to your grocery list.")
    return redirect(url_for("grocery.index"))


@bp.route("/<int:id>/remove", methods=("POST",))
@login_required
def remove(id):
    """Remove an item from the current user's grocery list."""
    db = get_db()
    item = db.execute(
        "SELECT id, user_id, item_name FROM grocery_items WHERE id = ?",
        (id,),
    ).fetchone()

    if item is None or item["user_id"] != g.user["id"]:
        flash("That grocery item was not found.")
        return redirect(url_for("grocery.index"))

    db.execute("DELETE FROM grocery_items WHERE id = ?", (id,))
    db.commit()
    flash(f"Removed '{item['item_name']}' from your list.")
    return redirect(url_for("grocery.index"))


@bp.route("/clear", methods=("POST",))
@login_required
def clear():
    """Remove all items from the current user's grocery list."""
    db = get_db()
    db.execute("DELETE FROM grocery_items WHERE user_id = ?", (g.user["id"],))
    db.commit()
    flash("Cleared your grocery list.")
    return redirect(url_for("grocery.index"))
