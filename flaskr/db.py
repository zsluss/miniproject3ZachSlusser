# INF601 - Advanced Programming in Python

# Zach Slusser

# Final Project

import sqlite3
from datetime import datetime

import click
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraints
        g.db.execute('PRAGMA foreign_keys = ON')

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


def ensure_schema_updates():
    """Create newer tables/indexes if they are missing in an existing DB."""
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
            UNIQUE(user_id, recipe_id)
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites (user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_favorites_recipe_id ON favorites (recipe_id)")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS grocery_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            amount TEXT,
            zone TEXT NOT NULL DEFAULT 'Other',
            found_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_grocery_items_user_id ON grocery_items (user_id)")

    grocery_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(grocery_items)").fetchall()
    }
    if "zone" not in grocery_columns:
        db.execute("ALTER TABLE grocery_items ADD COLUMN zone TEXT NOT NULL DEFAULT 'Other'")
    if "amount" not in grocery_columns:
        db.execute("ALTER TABLE grocery_items ADD COLUMN amount TEXT")
    if "found_at" not in grocery_columns:
        db.execute("ALTER TABLE grocery_items ADD COLUMN found_at TIMESTAMP")

    db.execute("UPDATE grocery_items SET zone = 'Other' WHERE zone IS NULL OR TRIM(zone) = ''")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS grocery_item_zone_memory (
            normalized_item TEXT PRIMARY KEY,
            zone TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.commit()


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)