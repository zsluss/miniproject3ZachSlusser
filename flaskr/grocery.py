# INF601 - Advanced Programming in Python

# Zach Slusser

# Final Project

import os

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("grocery", __name__, url_prefix="/grocery")

GROCERY_ZONES = [
    "Other",
    "Produce",
    "Meat & Seafood / Deli",
    "Dairy / Eggs",
    "Bakery",
    "Pantry / Dry Goods",
    "Frozen",
    "Household / Personal Care",
]


def _normalize_item_name(item_name):
    """Normalize grocery names so case and extra spacing don't create duplicates."""
    return " ".join(item_name.strip().split()).casefold()


def _clean_item_name(item_name):
    """Collapse extra internal whitespace while preserving user-entered casing."""
    return " ".join(item_name.strip().split())


def _learn_zone_for_item(db, item_name, zone):
    """Persist the latest chosen zone for a normalized grocery item name."""
    normalized_item = _normalize_item_name(item_name)
    if not normalized_item or zone not in GROCERY_ZONES:
        return

    db.execute(
        "INSERT INTO grocery_item_zone_memory (normalized_item, zone, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)"
        " ON CONFLICT(normalized_item) DO UPDATE SET zone = excluded.zone, updated_at = CURRENT_TIMESTAMP",
        (normalized_item, zone),
    )


def _get_learned_zone_for_item(db, item_name):
    """Return learned zone for item name, defaulting to Other if unknown."""
    normalized_item = _normalize_item_name(item_name)
    if not normalized_item:
        return "Other"

    learned = db.execute(
        "SELECT zone FROM grocery_item_zone_memory WHERE normalized_item = ?",
        (normalized_item,),
    ).fetchone()
    if learned and learned["zone"] in GROCERY_ZONES:
        return learned["zone"]

    # Fallback for older records before memory table existed.
    fallback = db.execute(
        "SELECT zone FROM grocery_items"
        " WHERE LOWER(TRIM(item_name)) = LOWER(TRIM(?))"
        " ORDER BY COALESCE(found_at, created_at) DESC, id DESC"
        " LIMIT 1",
        (item_name,),
    ).fetchone()
    if fallback and fallback["zone"] in GROCERY_ZONES:
        return fallback["zone"]

    return "Other"


def _fetch_active_items():
    """Return unfound grocery items grouped by configured zone order."""
    zone_order = " ".join(
        [f"WHEN ? THEN {index}" for index, _ in enumerate(GROCERY_ZONES)]
    )
    return get_db().execute(
        "SELECT gi.id, gi.user_id, gi.item_name, gi.amount, gi.zone, gi.created_at, u.username"
        " FROM grocery_items gi"
        " JOIN users u ON gi.user_id = u.id"
        " WHERE gi.found_at IS NULL"
        f" ORDER BY CASE gi.zone {zone_order} ELSE 999 END ASC, gi.created_at ASC, gi.id ASC",
        tuple(GROCERY_ZONES),
    ).fetchall()


def _get_settings_snapshot():
    """Return basic grocery and database stats for the settings page."""
    db = get_db()
    active_count = db.execute(
        "SELECT COUNT(*) AS count FROM grocery_items WHERE found_at IS NULL"
    ).fetchone()["count"]
    found_count = db.execute(
        "SELECT COUNT(*) AS count FROM grocery_items WHERE found_at IS NOT NULL"
    ).fetchone()["count"]

    database_path = current_app.config.get("DATABASE", "")
    database_size_bytes = os.path.getsize(database_path) if database_path and os.path.exists(database_path) else 0

    return {
        "active_count": active_count,
        "found_count": found_count,
        "database_size_bytes": database_size_bytes,
        "database_size_mb": round(database_size_bytes / (1024 * 1024), 2),
    }


@bp.route("/", methods=("GET",))
@login_required
def index():
    """Display the shared editable grocery planner for all logged-in users."""
    items = _fetch_active_items()
    last_removed_item = session.get("last_removed_grocery_item")
    return render_template(
        "grocery/index.html",
        items=items,
        zones=GROCERY_ZONES,
        last_removed_item=last_removed_item,
    )


@bp.route("/shopping", methods=("GET",))
@login_required
def shopping():
    """Display the shared in-store shopping view with only Found It actions."""
    items = _fetch_active_items()
    last_found_item = session.get("last_found_grocery_item")
    return render_template(
        "grocery/shopping.html",
        items=items,
        last_found_item=last_found_item,
    )


@bp.route("/settings", methods=("GET",))
@login_required
def settings():
    """Display grocery maintenance tools and database stats."""
    return render_template("grocery/settings.html", stats=_get_settings_snapshot())


@bp.route("/settings/purge-found", methods=("POST",))
@login_required
def purge_found_items():
    """Delete found grocery items older than the requested number of days."""
    days = request.form.get("days", default=90, type=int)
    if days is None or days < 1 or days > 3650:
        flash("Please choose a valid number of days between 1 and 3650.")
        return redirect(url_for("grocery.settings"))

    db = get_db()
    deleted = db.execute(
        "DELETE FROM grocery_items WHERE found_at IS NOT NULL AND found_at < datetime('now', ?)",
        (f"-{days} days",),
    ).rowcount
    db.commit()

    flash(f"Deleted {deleted} found item(s) older than {days} day(s).")
    return redirect(url_for("grocery.settings"))


@bp.route("/settings/compact", methods=("POST",))
@login_required
def compact_database():
    """Run VACUUM to compact the SQLite database file after cleanup."""
    db = get_db()
    db.commit()
    db.execute("VACUUM")
    flash("Database compacted successfully.")
    return redirect(url_for("grocery.settings"))


@bp.route("/add", methods=("POST",))
@login_required
def add():
    """Add an item to the current user's grocery list."""
    raw_item_text = request.form.get("item_name", "").strip()
    items_to_add = [item.strip() for item in raw_item_text.split(",") if item.strip()]

    if not items_to_add:
        flash("Please enter a grocery item before adding.")
        return redirect(url_for("grocery.index"))

    db = get_db()
    for raw_item_name in items_to_add:
        item_name = _clean_item_name(raw_item_name)
        zone = _get_learned_zone_for_item(db, item_name)
        db.execute(
            "INSERT INTO grocery_items (user_id, item_name, amount, zone, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (g.user["id"], item_name, None, zone),
        )
    db.commit()
    if len(items_to_add) == 1:
        flash(f"Added '{items_to_add[0]}' to your grocery list.")
    else:
        flash(f"Added {len(items_to_add)} items to your grocery list.")
    return redirect(url_for("grocery.index"))


@bp.route("/<int:id>/zone", methods=("POST",))
@login_required
def update_zone(id):
    """Update the grocery store zone for one item."""
    zone = request.form.get("zone", "").strip()

    if zone not in GROCERY_ZONES:
        flash("Please choose a valid store zone.")
        return redirect(url_for("grocery.index"))

    db = get_db()
    item = db.execute(
        "SELECT id, item_name FROM grocery_items WHERE id = ?",
        (id,),
    ).fetchone()

    if item is None:
        flash("That grocery item was not found.")
        return redirect(url_for("grocery.index"))

    db.execute("UPDATE grocery_items SET zone = ? WHERE id = ?", (zone, id))
    _learn_zone_for_item(db, item["item_name"], zone)
    db.commit()
    flash(f"Set '{item['item_name']}' to {zone}.")
    return redirect(url_for("grocery.index"))


@bp.route("/<int:id>/amount", methods=("POST",))
@login_required
def update_amount(id):
    """Update the optional amount/quantity for one grocery item."""
    amount_text = request.form.get("amount", "").strip()
    amount = amount_text or None

    db = get_db()
    item = db.execute(
        "SELECT id, item_name FROM grocery_items WHERE id = ?",
        (id,),
    ).fetchone()

    if item is None:
        flash("That grocery item was not found.")
        return redirect(url_for("grocery.index"))

    db.execute("UPDATE grocery_items SET amount = ? WHERE id = ?", (amount, id))
    db.commit()
    flash(f"Updated amount for '{item['item_name']}'.")
    return redirect(url_for("grocery.index"))


@bp.route("/<int:id>/remove", methods=("POST",))
@login_required
def remove(id):
    """Delete an item from the shared editable grocery planner."""
    db = get_db()
    item = db.execute(
        "SELECT id, user_id, item_name, amount, zone FROM grocery_items WHERE id = ?",
        (id,),
    ).fetchone()

    if item is None:
        flash("That grocery item was not found.")
        return redirect(url_for("grocery.index"))

    db.execute("DELETE FROM grocery_items WHERE id = ?", (id,))
    db.commit()
    session["last_removed_grocery_item"] = {
        "user_id": item["user_id"],
        "item_name": item["item_name"],
        "amount": item["amount"],
        "zone": item["zone"] or "Other",
    }
    flash(f"Removed '{item['item_name']}' from your list.")
    return redirect(url_for("grocery.index"))


@bp.route("/<int:id>/found", methods=("POST",))
@login_required
def mark_found(id):
    """Mark a grocery item as found during shopping."""
    db = get_db()
    item = db.execute(
        "SELECT id, item_name FROM grocery_items WHERE id = ?",
        (id,),
    ).fetchone()

    if item is None:
        flash("That grocery item was not found.")
        return redirect(url_for("grocery.shopping"))

    db.execute("UPDATE grocery_items SET found_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
    db.commit()
    session["last_found_grocery_item"] = {
        "id": item["id"],
        "item_name": item["item_name"],
    }
    flash(f"Marked '{item['item_name']}' as found.")
    return redirect(url_for("grocery.shopping"))


@bp.route("/undo-found", methods=("POST",))
@login_required
def undo_found():
    """Undo the most recent Found It action in this session."""
    last_found_item = session.get("last_found_grocery_item")

    if not last_found_item:
        flash("There is no recent Found It action to undo.")
        return redirect(url_for("grocery.shopping"))

    db = get_db()
    updated = db.execute(
        "UPDATE grocery_items SET found_at = NULL WHERE id = ?",
        (last_found_item["id"],),
    )
    db.commit()

    if updated.rowcount == 0:
        flash("That item could not be restored.")
    else:
        flash(f"Restored '{last_found_item['item_name']}' to shopping list.")
        session.pop("last_found_grocery_item", None)

    return redirect(url_for("grocery.shopping"))


@bp.route("/undo-remove", methods=("POST",))
@login_required
def undo_remove():
    """Restore the last removed grocery item for this session."""
    last_removed_item = session.get("last_removed_grocery_item")

    if not last_removed_item:
        flash("There is no recently removed item to undo.")
        return redirect(url_for("grocery.index"))

    db = get_db()
    db.execute(
        "INSERT INTO grocery_items (user_id, item_name, amount, zone, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            last_removed_item["user_id"],
            last_removed_item["item_name"],
            last_removed_item.get("amount"),
            last_removed_item["zone"],
        ),
    )
    db.commit()
    session.pop("last_removed_grocery_item", None)
    flash(f"Restored '{last_removed_item['item_name']}'.")
    return redirect(url_for("grocery.index"))


@bp.route("/clear", methods=("POST",))
@login_required
def clear():
    """Remove all items from the shared grocery list."""
    db = get_db()
    db.execute("DELETE FROM grocery_items")
    db.commit()
    flash("Cleared the shared grocery list.")
    return redirect(url_for("grocery.index"))
