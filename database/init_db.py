import sqlite3
from pathlib import Path


database_path = Path("database/bot.db").resolve()

with sqlite3.connect(database_path) as connection:
    rows = connection.execute(
        """
        SELECT
            guild_id,
            achievement_channel_id,
            achievements_enabled
        FROM guild_settings
        """
    ).fetchall()

    print(rows)