import sqlite3
import discord

from discord.ext import commands
from discord import app_commands

from utils.osu_api import OsuAPI
from utils.embeds import EmbedFactory
from utils.score_embed import ScoreEmbed

GUILD_ID = 1473125019692564542


class Scores(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="recent",
        description="View a player's most recent osu! play."
    )
    async def recent(
        self,
        interaction: discord.Interaction,
        username: str = None
    ):
        await interaction.response.defer()

        # Use linked account if no username is provided
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

        score = await OsuAPI.get_recent(osu_id)

        if score is None:
            embed = EmbedFactory.info(
            "No Recent Score",
            "No recent plays were found."
        )

            await interaction.followup.send(embed=embed)
            return

        # Fetch the complete score
        full_score = await OsuAPI.get_score(score["id"])

        # If the full lookup fails, fall back to the original score
        if full_score is not None:
            score = full_score

        print(score)

        embed = ScoreEmbed.recent(score)

        await interaction.followup.send(embed=embed)

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

        scores = await OsuAPI.get_top(osu_id)

        if not scores:
            embed = EmbedFactory.info(
                "No Scores",
                "No top scores were found."
            )

            await interaction.followup.send(embed=embed)
            return

        user = await OsuAPI.get_user_by_id(osu_id)

        embed = ScoreEmbed.top(user, scores)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Scores(bot))