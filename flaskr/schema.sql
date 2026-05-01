DROP TABLE IF EXISTS grocery_items;
DROP TABLE IF EXISTS grocery_item_zone_memory;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL,
    prep_minutes INTEGER DEFAULT 0,
    source_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX idx_recipes_user_id ON recipes (user_id);

CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE,
    UNIQUE(user_id, recipe_id)
);

CREATE INDEX idx_favorites_user_id ON favorites (user_id);
CREATE INDEX idx_favorites_recipe_id ON favorites (recipe_id);

CREATE TABLE grocery_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    amount TEXT,
    zone TEXT NOT NULL DEFAULT 'Other',
    found_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX idx_grocery_items_user_id ON grocery_items (user_id);

CREATE TABLE grocery_item_zone_memory (
    normalized_item TEXT PRIMARY KEY,
    zone TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);