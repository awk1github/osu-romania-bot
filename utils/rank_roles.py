import sqlite3
from pathlib import Path

import discord


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "bot.db"
)


class RankRoleService:
    SETTING_COLUMNS = (
        "rank_1_999_role_id",
        "rank_1000_9999_role_id",
        "rank_10000_99999_role_id",
        "rank_100000_999999_role_id",
        "rank_1000000_plus_role_id",
    )

    @staticmethod
    def get_target_role_id(
        global_rank: int | None,
        settings: sqlite3.Row,
    ) -> int | None:
        if global_rank is None or global_rank <= 0:
            return None

        if global_rank <= 999:
            return settings["rank_1_999_role_id"]

        if global_rank <= 9_999:
            return settings["rank_1000_9999_role_id"]

        if global_rank <= 99_999:
            return settings["rank_10000_99999_role_id"]

        if global_rank <= 999_999:
            return settings["rank_100000_999999_role_id"]

        return settings["rank_1000000_plus_role_id"]

    @staticmethod
    def get_settings(guild_id: int) -> sqlite3.Row | None:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row

            return connection.execute(
                """
                SELECT
                    rank_roles_enabled,
                    rank_1_999_role_id,
                    rank_1000_9999_role_id,
                    rank_10000_99999_role_id,
                    rank_100000_999999_role_id,
                    rank_1000000_plus_role_id
                FROM guild_settings
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()

    @staticmethod
    async def update_member(
        member: discord.Member,
        global_rank: int | None,
    ) -> bool:
        settings = RankRoleService.get_settings(member.guild.id)

        if settings is None or not settings["rank_roles_enabled"]:
            return False

        configured_role_ids = {
            settings[column]
            for column in RankRoleService.SETTING_COLUMNS
            if settings[column] is not None
        }

        target_role_id = RankRoleService.get_target_role_id(
            global_rank,
            settings,
        )

        current_rank_roles = [
            role
            for role in member.roles
            if role.id in configured_role_ids
        ]

        roles_to_remove = [
            role
            for role in current_rank_roles
            if role.id != target_role_id
        ]

        target_role = (
            member.guild.get_role(target_role_id)
            if target_role_id is not None
            else None
        )

        changed = False

        try:
            if roles_to_remove:
                await member.remove_roles(
                    *roles_to_remove,
                    reason="osu! global rank role update",
                )
                changed = True

            if (
                target_role is not None
                and target_role not in member.roles
            ):
                await member.add_roles(
                    target_role,
                    reason="osu! global rank role update",
                )
                changed = True

        except discord.Forbidden:
            print(
                f"Missing permission to update rank roles for "
                f"{member} in {member.guild}."
            )
            return False

        except discord.HTTPException as error:
            print(
                f"Discord error while updating rank roles for "
                f"{member}: {error}"
            )
            return False

        return changed