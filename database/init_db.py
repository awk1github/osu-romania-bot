import sqlite3


def initialize_database():
    with sqlite3.connect("database/bot.db") as connection:
        cursor = connection.cursor()

        # Moderation warnings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            date TEXT NOT NULL
        )
        """)

        cursor.execute("""
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

            last_updated TEXT
        )
        """)

        connection.commit()


initialize_database()