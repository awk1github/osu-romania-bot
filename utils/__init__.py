import sqlite3


DATABASE_PATH = "database/bot.db"


def get_database():
    """
    Returns a SQLite connection and cursor.
    """

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    return connection, cursor