from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "bot.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS osu_accounts (
    discord_id INTEGER PRIMARY KEY,
    osu_id INTEGER NOT NULL,
    osu_username TEXT NOT NULL,
    pp REAL,
    global_rank INTEGER,
    country_rank INTEGER,
    accuracy REAL,
    avatar_url TEXT,
    country_code TEXT,
    last_updated TEXT,
    achievements_enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    achievement_channel_id INTEGER,
    achievements_enabled INTEGER NOT NULL DEFAULT 1,
    autorole_id INTEGER,
    autorole_enabled INTEGER NOT NULL DEFAULT 0,
    welcome_channel_id INTEGER,
    welcome_enabled INTEGER NOT NULL DEFAULT 0,
    leave_channel_id INTEGER,
    leave_enabled INTEGER NOT NULL DEFAULT 0,
    rank_roles_enabled INTEGER NOT NULL DEFAULT 0,
    rank_1_999_role_id INTEGER,
    rank_1000_9999_role_id INTEGER,
    rank_10000_99999_role_id INTEGER,
    rank_100000_999999_role_id INTEGER,
    rank_1000000_plus_role_id INTEGER
);

CREATE TABLE IF NOT EXISTS osu_oauth_states (
    state TEXT PRIMARY KEY,
    discord_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_osu_accounts_osu_id
ON osu_accounts (osu_id);

CREATE TABLE IF NOT EXISTS osu_counties (
    osu_id INTEGER PRIMARY KEY,
    osu_username TEXT NOT NULL,
    county_code TEXT NOT NULL,
    county_name TEXT NOT NULL,
    county_rank INTEGER,
    pp REAL,
    global_rank INTEGER,
    country_rank INTEGER,
    avatar_url TEXT,
    last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS achievement_snapshots (
    osu_id INTEGER PRIMARY KEY,
    total_pp REAL,
    global_rank INTEGER,
    country_rank INTEGER,
    top_score_id INTEGER,
    top_score_pp REAL,
    top_10_json TEXT NOT NULL DEFAULT '[]',
    initialized INTEGER NOT NULL DEFAULT 0,
    last_checked TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osu_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_osu_accounts_osu_id
ON osu_accounts (osu_id);

CREATE INDEX IF NOT EXISTS idx_osu_counties_county_rank
ON osu_counties (county_code, county_rank);

CREATE INDEX IF NOT EXISTS idx_achievement_events_osu_id
ON achievement_events (osu_id);

CREATE INDEX IF NOT EXISTS idx_warnings_user_id
ON warnings (user_id);
"""

def initialize_database() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executescript(SCHEMA)
        connection.commit()

    print(f"Database initialized successfully: {DATABASE_PATH}")


if __name__ == "__main__":
    initialize_database()