import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from utils.cache import refresh_player
from utils.embeds import EmbedFactory
from utils.osu_api import OsuAPI
from utils.osu_embed import OsuEmbed
from views.profile import ProfileView


DATABASE_PATH = "database/bot.db"


class Profile(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

    # --------------------------------------------------
    # LINK
    # --------------------------------------------------

    @app_commands.command(
        name="link",
        description="Link your osu! account.",
    )
    async def link(
        self,
        interaction: discord.Interaction,
        username: str,
    ) -> None:
        await interaction.response.defer()

        user = await OsuAPI.get_user(username)

        if user is None:
            embed = EmbedFactory.error(
                "Player Not Found",
                "That osu! player doesn't exist.",
            )

            await interaction.followup.send(
                embed=embed
            )
            return

        statistics = user.get("statistics") or {}

        with sqlite3.connect(
            DATABASE_PATH
        ) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO osu_accounts (
                    discord_id,
                    osu_id,
                    osu_username,
                    pp,
                    global_rank,
                    country_rank,
                    accuracy,
                    avatar_url,
                    country_code,
                    last_updated
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    datetime('now')
                )
                """,
                (
                    interaction.user.id,
                    user["id"],
                    user["username"],
                    statistics.get("pp"),
                    statistics.get("global_rank"),
                    statistics.get("country_rank"),
                    statistics.get("hit_accuracy"),
                    user.get("avatar_url"),
                    user.get("country_code"),
                ),
            )

        embed = EmbedFactory.success(
            "Account Linked",
            (
                f"Discord: {interaction.user.mention}\n"
                f"osu!: **{user['username']}**"
            ),
        )

        await interaction.followup.send(
            embed=embed
        )

    # --------------------------------------------------
    # PROFILE
    # --------------------------------------------------

    @app_commands.command(
        name="profile",
        description="View an osu! profile.",
    )
    @app_commands.describe(
        username=(
            "The osu! username to view. "
            "Leave empty to view your linked account."
        ),
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        username: str | None = None,
    ) -> None:
        await interaction.response.defer()

        if username is None:
            with sqlite3.connect(
                DATABASE_PATH
            ) as connection:
                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT osu_id
                    FROM osu_accounts
                    WHERE discord_id = ?
                    """,
                    (interaction.user.id,),
                )

                row = cursor.fetchone()

            if row is None:
                embed = EmbedFactory.error(
                    "Account Not Linked",
                    (
                        "Use `/link <username>` first "
                        "or specify a username."
                    ),
                )

                await interaction.followup.send(
                    embed=embed
                )
                return

            osu_id = row[0]

        else:
            found_user = await OsuAPI.get_user(
                username
            )

            if found_user is None:
                embed = EmbedFactory.error(
                    "Player Not Found",
                    "That osu! player doesn't exist.",
                )

                await interaction.followup.send(
                    embed=embed
                )
                return

            osu_id = found_user["id"]

        try:
            await refresh_player(osu_id)
        except Exception as error:
            print(
                "[PROFILE] Player cache refresh failed: "
                f"{type(error).__name__}: {error}"
            )

        user = await OsuAPI.get_user(osu_id)

        if user is None:
            embed = EmbedFactory.error(
                "Player Not Found",
                (
                    "Couldn't retrieve that "
                    "osu! profile."
                ),
            )

            await interaction.followup.send(
                embed=embed
            )
            return

        embed = OsuEmbed.profile(user)

        view = ProfileView(
            author_id=interaction.user.id,
            user=user,
        )

        await interaction.followup.send(
            embed=embed,
            view=view,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        Profile(bot)
    )