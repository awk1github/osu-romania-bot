import asyncio
import sqlite3

from utils.osu_api import OsuAPI


DATABASE_PATH = "database/bot.db"


class ServerRecord:
    @staticmethod
    def _get_linked_users() -> list[dict]:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row

        try:
            cursor = connection.execute(
                """
                SELECT
                    discord_id,
                    osu_id,
                    osu_username
                FROM osu_accounts
                WHERE osu_id IS NOT NULL
                """
            )

            return [dict(row) for row in cursor.fetchall()]

        finally:
            connection.close()

    @staticmethod
    async def get_linked_users() -> list[dict]:
        return await asyncio.to_thread(
            ServerRecord._get_linked_users
        )

    @staticmethod
    async def _fetch_user_score(
        beatmap_id: int,
        linked_user: dict
    ) -> dict | None:
        try:
            response = await OsuAPI.get_user_beatmap_score(
                beatmap_id=beatmap_id,
                user_id=linked_user["osu_id"]
            )

        except Exception as error:
            print(
                f"Failed to fetch score for "
                f"{linked_user['osu_username']} "
                f"({linked_user['osu_id']}): "
                f"{type(error).__name__}: {error}"
            )
            return None

        if not response:
            return None

        score = response.get("score")

        if not score:
            scores = response.get("scores") or []
            score = scores[0] if scores else None

        if not score:
            return None

        # Attach information from our local database.
        score["_linked_discord_id"] = linked_user["discord_id"]
        score["_linked_osu_id"] = linked_user["osu_id"]
        score["_linked_osu_username"] = linked_user["osu_username"]
        score["_leaderboard_position"] = response.get("position")

        return score
