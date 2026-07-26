import sqlite3
import discord

from discord.ext import commands
from discord import app_commands

from utils.osu_api import OsuAPI
from utils.embeds import EmbedFactory
from utils.score_embed import ScoreEmbed
from utils.emojis import RANK_EMOJIS
from views.pagination import PaginationView

GUILD_ID = 1473125019692564542


class Scores(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="recent",
        description="View a player's most recent osu! play.",
    )
    async def recent(
        self,
        interaction: discord.Interaction,
        username: str | None = None,
    ):
        await interaction.response.defer()

        try:
            if username is None:
                with sqlite3.connect("database/bot.db") as connection:
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
                        "Use `/link <username>` first or specify a username.",
                    )

                    await interaction.followup.send(embed=embed)
                    return

                osu_id = row[0]

            else:
                user = await OsuAPI.get_user(username)

                if user is None:
                    embed = EmbedFactory.error(
                        "Player Not Found",
                        "That osu! player doesn't exist.",
                    )

                    await interaction.followup.send(embed=embed)
                    return

                osu_id = user["id"]

            profile = await OsuAPI.get_user(osu_id)
            score = await OsuAPI.get_recent(osu_id)

            if score is None:
                embed = EmbedFactory.info(
                    "No Recent Score",
                    "No recent plays were found.",
                )

                await interaction.followup.send(embed=embed)
                return

            mod_acronyms = []

            for mod in score.get("mods", []):
                if isinstance(mod, str):
                    mod_acronyms.append(mod.upper())

                elif isinstance(mod, dict):
                    acronym = mod.get("acronym")

                    if acronym:
                        mod_acronyms.append(acronym.upper())

            if "CL" in mod_acronyms:
                legacy_score_id = score.get("legacy_score_id")

                if legacy_score_id is not None:
                    full_score = await OsuAPI.get_legacy_score(
                        legacy_score_id,
                        mode="osu",
                    )
                else:
                    full_score = None
            else:
                full_score = await OsuAPI.get_score(
                    score["id"]
                )

            if full_score is not None:
                score = full_score

            print(score)

            if profile is not None:
                score["user"] = profile

            fc_pp = await OsuAPI.calculate_fc_pp(score)

            print(f"FC PP: {fc_pp}")

            embed = ScoreEmbed.recent(score)
            await interaction.followup.send(embed=embed)

        except Exception as error:
            print(f"Error in /recent: {error!r}")

            embed = EmbedFactory.error(
                "Recent Score Error",
                "Something went wrong while loading the recent score.",
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
            
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="top",
        description="View a player's top osu! plays."
    )
    async def top(
        self,
        interaction: discord.Interaction,
        username: str = None
    ):
        if not interaction.response.is_done():
            await interaction.response.defer()

        if username is None:

            connection = sqlite3.connect("database/bot.db")
            cursor = connection.cursor()

            cursor.execute(
                "SELECT osu_id FROM osu_accounts WHERE discord_id = ?",
                (interaction.user.id,)
            )

            row = cursor.fetchone()
            connection.close()

            if row is None:
                embed = EmbedFactory.error(
                    "Account Not Linked",
                    "Use `/link <username>` first or specify a username."
                )

                await interaction.followup.send(embed=embed)
                return

            osu_id = row[0]

        else:

            user = await OsuAPI.get_user(username)

            if user is None:
                embed = EmbedFactory.error(
                    "Player Not Found",
                    "That osu! player doesn't exist."
                )

                await interaction.followup.send(embed=embed)
                return

            osu_id = user["id"]

        scores = await OsuAPI.get_top(
            osu_id,
            limit=100,
        )

        if not scores:
            embed = EmbedFactory.info(
                "No Scores",
                "No top scores were found.",
            )

            await interaction.followup.send(embed=embed)
            return

        user = await OsuAPI.get_user(osu_id)

        if user is None:
            embed = EmbedFactory.error(
                "Player Error",
                "The player's profile could not be loaded.",
            )

            await interaction.followup.send(embed=embed)
            return

        per_page = 5

        max_pages = max(
            1,
            (len(scores) + per_page - 1) // per_page,
        )


        async def build_page(page: int) -> discord.Embed:
            return ScoreEmbed.top(
                user=user,
                scores=scores,
                page=page,
                per_page=per_page,
            )


        embed = await build_page(1)

        view = PaginationView(
            author_id=interaction.user.id,
            current_page=1,
            max_pages=max_pages,
            callback=build_page,
        )

        message = await interaction.followup.send(
            embed=embed,
            view=view,
            wait=True,
        )

        view.message = message


async def setup(bot):
    await bot.add_cog(Scores(bot))