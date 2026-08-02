import sqlite3

from utils.osu_api import OsuAPI


async def refresh_player(osu_id: int):

    user = await OsuAPI.get_user(osu_id)

    if user is None:
        return

    stats = user["statistics"]

    connection = sqlite3.connect("database/bot.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE osu_accounts
        SET
            osu_username=?,
            pp=?,
            global_rank=?,
            country_rank=?,
            accuracy=?,
            avatar_url=?,
            country_code=?,
            last_updated=datetime('now')
        WHERE osu_id=?
        """,
        (
            user["username"],
            stats["pp"],
            stats["global_rank"],
            stats["country_rank"],
            stats["hit_accuracy"],
            user["avatar_url"],
            user["country_code"],
            osu_id
        )
    )

    await OsuAPI.close_session()
    connection.commit()
    connection.close()