# INF601 - Advanced Programming in Python

# Zach Slusser

# Final Project

import os
from datetime import timedelta

from flask import Flask, g, redirect, render_template, url_for


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
        RANDOM_RECIPE_API_URL=os.environ.get('RANDOM_RECIPE_API_URL', ''),
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # home page
    @app.route('/')
    def index():
        # Logged-in users land on the regular recipe dashboard, it was taking them to an empty page before
        if g.get("user") is not None:
            return redirect(url_for("recipes.index"))

        return render_template('index.html')

    from . import db
    db.init_app(app)
    with app.app_context():
        db.ensure_schema_updates()

    from . import auth
    app.register_blueprint(auth.bp)

    from . import recipes
    app.register_blueprint(recipes.bp)

    from . import grocery
    app.register_blueprint(grocery.bp)

    return app