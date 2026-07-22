import sqlite3
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.counties import ROMANIAN_COUNTIES
from utils.county_fetcher import CountyFetcher
from views.county_leaderboard import (
    CountyLeaderboardView,
)


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "bot.db"
)


class CountyCommands(
    commands.GroupCog,
    group_name="county",
    group_description="Romanian osu! county commands.",
):
    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

    # --------------------------------------------------
    # COUNTY LEADERBOARD
    # --------------------------------------------------

    @app_commands.command(
        name="leaderboard",
        description=(
            "View the osu! leaderboard "
            "for a Romanian county."
        ),
    )
    @app_commands.describe(
        county="The Romanian county to display.",
        page="The leaderboard page.",
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        county: str,
        page: app_commands.Range[int, 1, 100] = 1,
    ) -> None:
        await interaction.response.defer()

        county_code = self.resolve_county_code(
            county
        )

        if county_code is None:
            await interaction.followup.send(
                "That county could not be found.",
                ephemeral=True,
            )
            return

        if not DATABASE_PATH.exists():
            await interaction.followup.send(
                "The bot database could not be found.",
                ephemeral=True,
            )
            return

        county_name = ROMANIAN_COUNTIES[
            county_code
        ]

        try:
            view = CountyLeaderboardView(
                author_id=interaction.user.id,
                county_code=county_code,
                county_name=county_name,
                current_page=page,
            )

            if view.total_players == 0:
                await interaction.followup.send(
                    (
                        "No leaderboard data has been "
                        "stored for "
                        f"**{county_name}** yet."
                    ),
                    ephemeral=True,
                )
                return

            if page > view.total_pages:
                await interaction.followup.send(
                    (
                        f"Page **{page}** does not exist.\n"
                        f"**{county_name}** currently has "
                        f"**{view.total_pages}** page(s)."
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
                "[COUNTY] Database error while loading "
                f"{county_name}: {error}"
            )

            await interaction.followup.send(
                (
                    "A database error occurred while "
                    "loading the leaderboard."
                ),
                ephemeral=True,
            )

    # --------------------------------------------------
    # COUNTY SYNC
    # --------------------------------------------------

    @app_commands.command(
        name="sync",
        description=(
            "Update all Romanian county leaderboards."
        ),
    )
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def sync(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        started_at = time.monotonic()

        try:
            total_players = (
                await CountyFetcher.sync_all_counties()
            )

        except Exception as error:
            print(
                "[COUNTY] County sync failed: "
                f"{type(error).__name__}: {error}"
            )

            await interaction.followup.send(
                (
                    "The county synchronization failed.\n"
                    "Check the bot terminal for "
                    "the full error."
                ),
                ephemeral=True,
            )
            return

        elapsed_seconds = (
            time.monotonic() - started_at
        )

        embed = discord.Embed(
            title="✅ County Leaderboards Updated",
            description=(
                f"**Players saved:** "
                f"{total_players:,}\n"
                f"**Counties checked:** "
                f"{len(ROMANIAN_COUNTIES)}\n"
                f"**Time:** "
                f"{elapsed_seconds:.1f} seconds"
            ),
            color=discord.Color.green(),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # AUTOCOMPLETE
    # --------------------------------------------------

    @leaderboard.autocomplete("county")
    async def county_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        del interaction

        current = current.casefold().strip()

        choices: list[
            app_commands.Choice[str]
        ] = []

        for county_code, county_name in (
            ROMANIAN_COUNTIES.items()
        ):
            searchable_text = (
                f"{county_name} {county_code}"
            ).casefold()

            if (
                current
                and current not in searchable_text
            ):
                continue

            choices.append(
                app_commands.Choice(
                    name=(
                        f"{county_name} "
                        f"({county_code})"
                    ),
                    value=county_code,
                )
            )

            if len(choices) >= 25:
                break

        return choices

    # --------------------------------------------------
    # COUNTY RESOLVER
    # --------------------------------------------------

    @staticmethod
    def resolve_county_code(
        county: str,
    ) -> str | None:
        county = county.strip()
        code = county.upper()

        if code.startswith("RO-"):
            code = code[3:]

        if code in ROMANIAN_COUNTIES:
            return code

        for county_code, county_name in (
            ROMANIAN_COUNTIES.items()
        ):
            if (
                county_name.casefold()
                == county.casefold()
            ):
                return county_code

        return None

    # --------------------------------------------------
    # ERROR HANDLER
    # --------------------------------------------------

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(
            error,
            app_commands.MissingPermissions,
        ):
            message = (
                "You need the Administrator "
                "permission to use this command."
            )
        else:
            print(
                "[COUNTY] Command error: "
                f"{type(error).__name__}: {error}"
            )

            message = (
                "An unexpected error occurred while "
                "running the county command."
            )

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        CountyCommands(bot)
    )