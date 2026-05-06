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


def _get_current_group_id(db):
    """Return the current user's grocery group id, creating a personal one if needed."""
    user = db.execute(
        "SELECT id, grocery_group_id FROM users WHERE id = ?",
        (g.user["id"],),
    ).fetchone()

    if user is None:
        return None

    group_id = user["grocery_group_id"] or user["id"]
    if user["grocery_group_id"] is None:
        db.execute(
            "UPDATE users SET grocery_group_id = ? WHERE id = ?",
            (group_id, user["id"]),
        )
        db.commit()

    return group_id


def _merge_grocery_groups(db, first_group_id, second_group_id):
    """Merge two grocery groups so every member shares one list."""
    target_group_id = min(first_group_id, second_group_id)
    db.execute(
        "UPDATE users SET grocery_group_id = ? WHERE grocery_group_id IN (?, ?)",
        (target_group_id, first_group_id, second_group_id),
    )


def _fetch_pending_requests(db):
    """Return incoming and outgoing pending share requests for settings."""
    incoming = db.execute(
        "SELECT gsr.id, gsr.created_at, requester.username AS requester_username"
        " FROM grocery_share_requests gsr"
        " JOIN users requester ON requester.id = gsr.requester_id"
        " WHERE gsr.recipient_id = ? AND gsr.status = 'pending'"
        " ORDER BY gsr.created_at DESC, gsr.id DESC",
        (g.user["id"],),
    ).fetchall()

    outgoing = db.execute(
        "SELECT gsr.id, gsr.created_at, recipient.username AS recipient_username"
        " FROM grocery_share_requests gsr"
        " JOIN users recipient ON recipient.id = gsr.recipient_id"
        " WHERE gsr.requester_id = ? AND gsr.status = 'pending'"
        " ORDER BY gsr.created_at DESC, gsr.id DESC",
        (g.user["id"],),
    ).fetchall()

    return incoming, outgoing


def _get_group_members(db, group_id):
    """Return usernames in the active grocery sharing group."""
    return db.execute(
        "SELECT username FROM users WHERE grocery_group_id = ? ORDER BY username COLLATE NOCASE",
        (group_id,),
    ).fetchall()


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


def _fetch_active_items(group_id):
    """Return unfound grocery items for the active sharing group."""
    zone_order = " ".join(
        [f"WHEN ? THEN {index}" for index, _ in enumerate(GROCERY_ZONES)]
    )
    return get_db().execute(
        "SELECT gi.id, gi.user_id, gi.item_name, gi.amount, gi.zone, gi.created_at, u.username"
        " FROM grocery_items gi"
        " JOIN users u ON gi.user_id = u.id"
        " JOIN users owner ON owner.id = gi.user_id"
        " WHERE gi.found_at IS NULL"
        " AND owner.grocery_group_id = ?"
        f" ORDER BY CASE gi.zone {zone_order} ELSE 999 END ASC, gi.created_at ASC, gi.id ASC",
        (group_id, *GROCERY_ZONES),
    ).fetchall()


def _get_settings_snapshot(group_id):
    """Return grocery and database stats for the current sharing group."""
    db = get_db()
    active_count = db.execute(
        "SELECT COUNT(*) AS count"
        " FROM grocery_items gi"
        " JOIN users u ON u.id = gi.user_id"
        " WHERE gi.found_at IS NULL AND u.grocery_group_id = ?",
        (group_id,),
    ).fetchone()["count"]
    found_count = db.execute(
        "SELECT COUNT(*) AS count"
        " FROM grocery_items gi"
        " JOIN users u ON u.id = gi.user_id"
        " WHERE gi.found_at IS NOT NULL AND u.grocery_group_id = ?",
        (group_id,),
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
    """Display the grocery planner for the current sharing group."""
    db = get_db()
    group_id = _get_current_group_id(db)
    items = _fetch_active_items(group_id)
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
    """Display in-store shopping view for the current sharing group."""
    db = get_db()
    group_id = _get_current_group_id(db)
    items = _fetch_active_items(group_id)
    last_found_item = session.get("last_found_grocery_item")
    return render_template(
        "grocery/shopping.html",
        items=items,
        last_found_item=last_found_item,
    )


@bp.route("/settings", methods=("GET",))
@login_required
def settings():
    """Display grocery maintenance tools and sharing settings."""
    db = get_db()
    group_id = _get_current_group_id(db)
    incoming_requests, outgoing_requests = _fetch_pending_requests(db)
    group_members = _get_group_members(db, group_id)
    return render_template(
        "grocery/settings.html",
        stats=_get_settings_snapshot(group_id),
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests,
        group_members=group_members,
    )


@bp.route("/settings/share-request", methods=("POST",))
@login_required
def create_share_request():
    """Send a grocery sharing request to another username."""
    target_username = request.form.get("target_username", "").strip()
    if not target_username:
        flash("Enter a username to invite.")
        return redirect(url_for("grocery.settings"))

    db = get_db()
    current_group_id = _get_current_group_id(db)

    target_user = db.execute(
        "SELECT id, username, grocery_group_id FROM users WHERE username = ? COLLATE NOCASE",
        (target_username,),
    ).fetchone()

    if target_user is None:
        flash("That username was not found.")
        return redirect(url_for("grocery.settings"))

    if target_user["id"] == g.user["id"]:
        flash("You cannot invite yourself.")
        return redirect(url_for("grocery.settings"))

    target_group_id = target_user["grocery_group_id"] or target_user["id"]
    if target_group_id == current_group_id:
        flash(f"You are already sharing a grocery list with {target_user['username']}.")
        return redirect(url_for("grocery.settings"))

    existing_pending = db.execute(
        "SELECT id FROM grocery_share_requests"
        " WHERE status = 'pending'"
        " AND ((requester_id = ? AND recipient_id = ?) OR (requester_id = ? AND recipient_id = ?))",
        (g.user["id"], target_user["id"], target_user["id"], g.user["id"]),
    ).fetchone()
    if existing_pending is not None:
        flash("A pending grocery share request already exists between you and that user.")
        return redirect(url_for("grocery.settings"))

    db.execute(
        "INSERT INTO grocery_share_requests (requester_id, recipient_id, status) VALUES (?, ?, 'pending')",
        (g.user["id"], target_user["id"]),
    )
    db.commit()
    flash(f"Share request sent to {target_user['username']}.")
    return redirect(url_for("grocery.settings"))


@bp.route("/settings/share-request/<int:request_id>/respond", methods=("POST",))
@login_required
def respond_share_request(request_id):
    """Accept or decline a pending grocery share request."""
    decision = request.form.get("decision", "").strip().lower()
    if decision not in {"accept", "decline"}:
        flash("Choose accept or decline.")
        return redirect(url_for("grocery.settings"))

    db = get_db()
    share_request = db.execute(
        "SELECT id, requester_id, recipient_id"
        " FROM grocery_share_requests"
        " WHERE id = ? AND recipient_id = ? AND status = 'pending'",
        (request_id, g.user["id"]),
    ).fetchone()

    if share_request is None:
        flash("That request is no longer available.")
        return redirect(url_for("grocery.settings"))

    requester = db.execute(
        "SELECT id, grocery_group_id, username FROM users WHERE id = ?",
        (share_request["requester_id"],),
    ).fetchone()
    recipient = db.execute(
        "SELECT id, grocery_group_id FROM users WHERE id = ?",
        (share_request["recipient_id"],),
    ).fetchone()

    if decision == "accept" and requester is not None and recipient is not None:
        requester_group_id = requester["grocery_group_id"] or requester["id"]
        recipient_group_id = recipient["grocery_group_id"] or recipient["id"]
        _merge_grocery_groups(db, requester_group_id, recipient_group_id)
        db.execute(
            "UPDATE grocery_share_requests SET status = 'accepted', responded_at = CURRENT_TIMESTAMP WHERE id = ?",
            (share_request["id"],),
        )
        db.execute(
            "UPDATE grocery_share_requests"
            " SET status = 'declined', responded_at = CURRENT_TIMESTAMP"
            " WHERE status = 'pending' AND id != ?"
            " AND ((requester_id = ? AND recipient_id = ?) OR (requester_id = ? AND recipient_id = ?))",
            (
                share_request["id"],
                share_request["requester_id"],
                share_request["recipient_id"],
                share_request["recipient_id"],
                share_request["requester_id"],
            ),
        )
        db.commit()
        flash(f"You are now sharing a grocery list with {requester['username']}.")
        return redirect(url_for("grocery.settings"))

    db.execute(
        "UPDATE grocery_share_requests SET status = 'declined', responded_at = CURRENT_TIMESTAMP WHERE id = ?",
        (share_request["id"],),
    )
    db.commit()
    flash("Grocery share request declined.")
    return redirect(url_for("grocery.settings"))


@bp.route("/settings/purge-found", methods=("POST",))
@login_required
def purge_found_items():
    """Delete found grocery items older than the requested number of days."""
    days = request.form.get("days", default=90, type=int)
    if days is None or days < 1 or days > 3650:
        flash("Please choose a valid number of days between 1 and 3650.")
        return redirect(url_for("grocery.settings"))

    db = get_db()
    group_id = _get_current_group_id(db)
    deleted = db.execute(
        "DELETE FROM grocery_items"
        " WHERE found_at IS NOT NULL"
        " AND found_at < datetime('now', ?)"
        " AND user_id IN (SELECT id FROM users WHERE grocery_group_id = ?)",
        (f"-{days} days", group_id),
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
    group_id = _get_current_group_id(db)
    item = db.execute(
        "SELECT gi.id, gi.item_name"
        " FROM grocery_items gi"
        " JOIN users u ON u.id = gi.user_id"
        " WHERE gi.id = ? AND u.grocery_group_id = ?",
        (id, group_id),
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
    group_id = _get_current_group_id(db)
    item = db.execute(
        "SELECT gi.id, gi.item_name"
        " FROM grocery_items gi"
        " JOIN users u ON u.id = gi.user_id"
        " WHERE gi.id = ? AND u.grocery_group_id = ?",
        (id, group_id),
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
    group_id = _get_current_group_id(db)
    item = db.execute(
        "SELECT gi.id, gi.user_id, gi.item_name, gi.amount, gi.zone"
        " FROM grocery_items gi"
        " JOIN users u ON u.id = gi.user_id"
        " WHERE gi.id = ? AND u.grocery_group_id = ?",
        (id, group_id),
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
    group_id = _get_current_group_id(db)
    item = db.execute(
        "SELECT gi.id, gi.item_name"
        " FROM grocery_items gi"
        " JOIN users u ON u.id = gi.user_id"
        " WHERE gi.id = ? AND u.grocery_group_id = ?",
        (id, group_id),
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
    group_id = _get_current_group_id(db)
    updated = db.execute(
        "UPDATE grocery_items SET found_at = NULL"
        " WHERE id = ?"
        " AND user_id IN (SELECT id FROM users WHERE grocery_group_id = ?)",
        (last_found_item["id"], group_id),
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
    group_id = _get_current_group_id(db)
    owner_is_in_group = db.execute(
        "SELECT 1 FROM users WHERE id = ? AND grocery_group_id = ?",
        (last_removed_item["user_id"], group_id),
    ).fetchone()
    if owner_is_in_group is None:
        flash("That item can no longer be restored in your current shared list.")
        session.pop("last_removed_grocery_item", None)
        return redirect(url_for("grocery.index"))

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
    """Remove all items from the current grocery sharing group."""
    db = get_db()
    group_id = _get_current_group_id(db)
    db.execute(
        "DELETE FROM grocery_items WHERE user_id IN (SELECT id FROM users WHERE grocery_group_id = ?)",
        (group_id,),
    )
    db.commit()
    flash("Cleared your shared grocery list.")
    return redirect(url_for("grocery.index"))
