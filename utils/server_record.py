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

    @staticmethod
    def _score_value(score: dict) -> int:
        value = (
            score.get("total_score")
            or score.get("legacy_total_score")
            or score.get("score")
            or 0
        )

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    async def get_top_for_beatmap(
        beatmap_id: int | str,
        limit: int = 3
    ) -> list[dict]:
        linked_users = await ServerRecord.get_linked_users()

        if not linked_users:
            return []

        semaphore = asyncio.Semaphore(3)

        async def fetch_with_limit(linked_user: dict):
            async with semaphore:
                return await ServerRecord._fetch_user_score(
                    beatmap_id=int(beatmap_id),
                    linked_user=linked_user,
                )
            
        tasks = [
            fetch_with_limit(user)
            for user in linked_users
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        valid_scores = [
            score
            for score in results
            if score is not None
        ]

        valid_scores.sort(
            key=ServerRecord._score_value,
            reverse=True
        )

        return valid_scores[:limit]