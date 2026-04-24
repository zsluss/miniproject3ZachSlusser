# INF601 - Advanced Programming in Python

# Zach Slusser

# Mini Project 3

import functools
import json
import urllib.error
import urllib.parse
import urllib.request

from flask import (
    abort,
    Blueprint,
    current_app,
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
    """Display all recipes or only the current user's recipes."""
    show_mine = request.args.get("mine", "0") == "1"
    search_query = request.args.get("q", "").strip()

    if show_mine and g.user is None:
        flash("Please log in to view your recipes.")
        return redirect(url_for("auth.login"))

    db = get_db()
    user_id = g.user["id"] if g.user else None
    
    # Build base query with favorite status
    if show_mine:
        base_query = (
            "SELECT r.id, r.title, r.ingredients, r.instructions, r.prep_minutes, r.created_at, r.user_id, u.username,"
            " CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END AS is_favorited"
            " FROM recipes r"
            " JOIN users u ON r.user_id = u.id"
            " LEFT JOIN favorites f ON r.id = f.recipe_id AND f.user_id = ?"
            " WHERE r.user_id = ?"
        )
        params = [user_id, user_id]
    else:
        base_query = (
            "SELECT r.id, r.title, r.ingredients, r.instructions, r.prep_minutes, r.created_at, r.user_id, u.username,"
            " CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END AS is_favorited"
            " FROM recipes r"
            " JOIN users u ON r.user_id = u.id"
            " LEFT JOIN favorites f ON r.id = f.recipe_id AND f.user_id = ?"
            " WHERE 1=1"
        )
        params = [user_id]
    
    # Add search filter
    if search_query:
        base_query += " AND (r.title LIKE ? OR r.ingredients LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    
    # Sort: favorites first (only for logged-in users), then by created_at DESC
    if user_id:
        base_query += " ORDER BY is_favorited DESC, r.created_at DESC"
    else:
        base_query += " ORDER BY r.created_at DESC"
    
    recipes = db.execute(base_query, params).fetchall()

    return render_template("recipes/index.html", recipes=recipes, showing_mine=show_mine, search_query=search_query)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new recipe."""
    if request.method == "POST":
        title = request.form["title"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]
        prep_minutes = request.form.get("prep_minutes", 0, type=int)
        source_url = request.form.get("source_url", "").strip()
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
                "INSERT INTO recipes (user_id, title, ingredients, instructions, prep_minutes, source_url, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (g.user["id"], title, ingredients, instructions, prep_minutes, source_url or None),
            )
            db.commit()
            return redirect(url_for("recipes.index"))

    return render_template("recipes/create.html")


@bp.route("/<int:id>/detail", methods=("GET",))
def detail(id):
    """View recipe details."""
    recipe = get_recipe(id, check_author=False)
    
    # Check if current user has favorited this recipe
    is_favorited = False
    if g.user:
        db = get_db()
        fav = db.execute(
            "SELECT id FROM favorites WHERE user_id = ? AND recipe_id = ?",
            (g.user["id"], id),
        ).fetchone()
        is_favorited = fav is not None
    
    return render_template("recipes/detail.html", recipe=recipe, is_favorited=is_favorited)


@bp.route("/<int:id>/edit", methods=("GET", "POST"))
@login_required
def edit(id):
    """Edit a recipe."""
    recipe = get_recipe(id)

    if request.method == "POST":
        title = request.form["title"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]
        prep_minutes = request.form.get("prep_minutes", 0, type=int)
        source_url = request.form.get("source_url", "").strip()
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
                "UPDATE recipes SET title = ?, ingredients = ?, instructions = ?, prep_minutes = ?, source_url = ? WHERE id = ?",
                (title, ingredients, instructions, prep_minutes, source_url or None, id),
            )
            db.commit()
            return redirect(url_for("recipes.detail", id=id))

    return render_template("recipes/edit.html", recipe=recipe)


@bp.route("/random", methods=("GET",))
@login_required
def random_recipe():
    """Display a random MealDB meal and optional category-filtered meal list."""
    random_url = "https://www.themealdb.com/api/json/v1/1/random.php"
    categories_url = "https://www.themealdb.com/api/json/v1/1/categories.php"
    selected_category = request.args.get("category", "").strip()
    selected_meal_id = request.args.get("meal_id", "").strip()

    recipe = None
    categories = []
    filtered_meals = []
    selected_meal = None

    try:
        random_data = _fetch_json(random_url)
        recipe = _normalize_api_recipe(random_data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        flash("Could not load a random meal right now.")

    try:
        categories_data = _fetch_json(categories_url)
        categories = [
            item.get("strCategory")
            for item in categories_data.get("categories", [])
            if item.get("strCategory")
        ]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        flash("Could not load meal categories right now.")

    if selected_category:
        filter_query = urllib.parse.urlencode({"c": selected_category})
        filter_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?{filter_query}"
        try:
            filtered_data = _fetch_json(filter_url)
            filtered_meals = filtered_data.get("meals") or []
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            flash("Could not load meals for that category right now.")

    if selected_meal_id:
        lookup_query = urllib.parse.urlencode({"i": selected_meal_id})
        lookup_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?{lookup_query}"
        try:
            selected_data = _fetch_json(lookup_url)
            selected_meal = _normalize_api_recipe(selected_data)
            if selected_meal is None:
                flash("Could not find details for that meal.")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            flash("Could not load meal details right now.")

    main_recipe = selected_meal or recipe

    return render_template(
        "recipes/random.html",
        main_recipe=main_recipe,
        categories=categories,
        selected_category=selected_category,
        filtered_meals=filtered_meals,
        selected_meal_id=selected_meal_id,
    )


@bp.route("/add-from-api", methods=("POST",))
@login_required
def add_from_api():
    """Save a MealDB recipe to the user's collection."""
    title = request.form.get("title", "").strip()
    ingredients = request.form.get("ingredients", "").strip()
    instructions = request.form.get("instructions", "").strip()
    source_url = request.form.get("source_url", "").strip()
    error = None

    if not title:
        error = "Recipe title is required."
    elif not ingredients:
        error = "Ingredients are required."
    elif not instructions:
        error = "Instructions are required."

    if error is not None:
        flash(error)
    else:
        db = get_db()
        db.execute(
            "INSERT INTO recipes (user_id, title, ingredients, instructions, prep_minutes, source_url, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (g.user["id"], title, ingredients, instructions, 0, source_url or None),
        )
        db.commit()
        flash(f"Recipe '{title}' added to your collection!")

    return redirect(url_for("recipes.random_recipe"))


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a recipe."""
    recipe = get_recipe(id)
    
    db = get_db()
    db.execute("DELETE FROM recipes WHERE id = ?", (id,))
    db.commit()
    flash("Recipe deleted successfully.")
    return redirect(url_for("recipes.index"))


@bp.route("/<int:id>/favorite", methods=("POST",))
@login_required
def toggle_favorite(id):
    """Toggle favorite status for a recipe."""
    # Verify recipe exists
    recipe = get_recipe(id, check_author=False)
    
    db = get_db()
    user_id = g.user["id"]
    
    # Check if already favorited
    existing = db.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND recipe_id = ?",
        (user_id, id),
    ).fetchone()
    
    if existing:
        # Remove from favorites
        db.execute("DELETE FROM favorites WHERE user_id = ? AND recipe_id = ?", (user_id, id))
        flash(f"Removed '{recipe['title']}' from favorites.")
    else:
        # Add to favorites
        db.execute(
            "INSERT INTO favorites (user_id, recipe_id, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (user_id, id),
        )
        flash(f"Added '{recipe['title']}' to favorites!")
    
    db.commit()
    return redirect(request.referrer or url_for("recipes.index"))


def get_recipe(id, check_author=True):
    """Get a recipe by ID."""
    recipe = get_db().execute(
        "SELECT r.id, r.title, r.ingredients, r.instructions, r.prep_minutes, r.source_url, r.created_at, r.user_id, u.username"
        " FROM recipes r JOIN users u ON r.user_id = u.id"
        " WHERE r.id = ?",
        (id,),
    ).fetchone()

    if recipe is None:
        abort(404, f"Recipe id {id} does not exist.")

    if check_author and recipe["user_id"] != g.user["id"]:
        abort(403)

    return recipe


def _normalize_api_recipe(data):
    """Normalize MealDB random meal response into template-friendly fields."""
    if isinstance(data, list):
        if not data:
            return None
        data = data[0]

    if isinstance(data, dict) and "meals" in data and isinstance(data["meals"], list):
        if not data["meals"]:
            return None
        data = data["meals"][0]

    if not isinstance(data, dict):
        return None

    title = data.get("strMeal")
    ingredients = _build_mealdb_ingredients(data)
    instructions = data.get("strInstructions")
    image = data.get("strMealThumb")
    source_url = data.get("strSource")
    youtube_url = data.get("strYoutube")
    category = data.get("strCategory")
    area = data.get("strArea")

    if not title:
        return None

    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions,
        "image": image,
        "preview_image": _build_preview_image_url(image),
        "source_url": source_url,
        "youtube_url": youtube_url,
        "category": category,
        "area": area,
    }


def _build_mealdb_ingredients(data):
    """Build readable ingredient lines from MealDB numbered fields."""
    lines = []
    for index in range(1, 21):
        ingredient = (data.get(f"strIngredient{index}") or "").strip()
        measure = (data.get(f"strMeasure{index}") or "").strip()

        if ingredient:
            lines.append(f"{measure} {ingredient}".strip())

    return "\n".join(lines)


def _fetch_json(url):
    """Fetch and parse JSON from a URL."""
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def _build_preview_image_url(image_url):
    """Return TheMealDB small preview URL for a meal image."""
    return f"{image_url}/preview" if image_url else None
