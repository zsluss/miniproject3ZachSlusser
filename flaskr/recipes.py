# INF601 - Advanced Programming in Python

# Zach Slusser

# Mini Project 3

import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from flaskr.db import get_db
from flaskr.auth import login_required

bp = Blueprint("recipes", __name__, url_prefix="/recipes")


@bp.route("/")
def index():
    """Display all recipes."""
    db = get_db()
    recipes = db.execute(
        "SELECT r.id, r.title, r.ingredients, r.instructions, r.prep_minutes, r.created_at, r.user_id, u.username"
        " FROM recipes r JOIN users u ON r.user_id = u.id"
        " ORDER BY r.created_at DESC"
    ).fetchall()
    return render_template("recipes/index.html", recipes=recipes)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new recipe."""
    if request.method == "POST":
        title = request.form["title"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]
        prep_minutes = request.form.get("prep_minutes", 0, type=int)
        error = None

        if not title:
            error = "Title is required."
        elif not ingredients:
            error = "Ingredients are required."
        elif not instructions:
            error = "Instructions are required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO recipes (user_id, title, ingredients, instructions, prep_minutes, created_at)"
                " VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (g.user["id"], title, ingredients, instructions, prep_minutes),
            )
            db.commit()
            return redirect(url_for("recipes.index"))

    return render_template("recipes/create.html")


@bp.route("/<int:id>/detail", methods=("GET",))
def detail(id):
    """View recipe details."""
    recipe = get_recipe(id)
    return render_template("recipes/detail.html", recipe=recipe)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a recipe."""
    recipe = get_recipe(id)
    
    if recipe["user_id"] != g.user["id"]:
        flash("You do not have permission to delete this recipe.")
        return redirect(url_for("recipes.index"))
    
    db = get_db()
    db.execute("DELETE FROM recipes WHERE id = ?", (id,))
    db.commit()
    flash("Recipe deleted successfully.")
    return redirect(url_for("recipes.index"))


def get_recipe(id, check_author=True):
    """Get a recipe by ID."""
    recipe = get_db().execute(
        "SELECT r.id, r.title, r.ingredients, r.instructions, r.prep_minutes, r.created_at, r.user_id, u.username"
        " FROM recipes r JOIN users u ON r.user_id = u.id"
        " WHERE r.id = ?",
        (id,),
    ).fetchone()

    if recipe is None:
        flash(f"Recipe not found.")
        return redirect(url_for("recipes.index"))

    if check_author and recipe["user_id"] != g.user["id"]:
        flash("You do not have permission to view this recipe.")
        return redirect(url_for("recipes.index"))

    return recipe
