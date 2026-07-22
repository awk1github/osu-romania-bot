import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedFactory
from views.leaderboard import ServerLeaderboardView


DATABASE_PATH = Path("database/bot.db")


class Leaderboard(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description=(
            "View the osu!Romania server leaderboard."
        ),
    )
    @app_commands.describe(
        page="The leaderboard page.",
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        page: app_commands.Range[int, 1, 100] = 1,
    ) -> None:
        await interaction.response.defer()

        if not DATABASE_PATH.exists():
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Database Not Found",
                    "The bot database could not be found.",
                ),
                ephemeral=True,
            )
            return

        try:
            view = ServerLeaderboardView(
                author_id=interaction.user.id,
                current_page=page,
            )

            if view.total_players == 0:
                embed = EmbedFactory.info(
                    "Leaderboard Empty",
                    (
                        "Nobody has linked their "
                        "osu! account yet."
                    ),
                )

                await interaction.followup.send(
                    embed=embed
                )
                return

            if page > view.total_pages:
                await interaction.followup.send(
                    embed=EmbedFactory.info(
                        "Page Not Found",
                        (
                            f"Page **{page}** does not exist.\n"
                            "The leaderboard currently has "
                            f"**{view.total_pages}** page(s)."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            embed = await view.build_page(page)

            await interaction.followup.send(
                embed=embed,
                view=view,
            )

        except sqlite3.Error as error:
            print(
                "[LEADERBOARD] Database error: "
                f"{type(error).__name__}: {error}"
            )

            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Database Error",
                    (
                        "A database error occurred while "
                        "loading the leaderboard."
                    ),
                ),
                ephemeral=True,
            )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        Leaderboard(bot)
    )