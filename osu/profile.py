import sqlite3
import discord

from discord.ext import commands
from discord import app_commands

from utils.osu_api import OsuAPI
from utils.embeds import EmbedFactory
from utils.osu_embed import OsuEmbed
from utils.cache import refresh_player

GUILD_ID = 1473125019692564542


class Profile(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="link",
        description="Link your osu! account."
    )
    async def link(
        self,
        interaction: discord.Interaction,
        username: str
    ):
        await interaction.response.defer()

        user = await OsuAPI.get_user(username)

        if user is None:
            embed = EmbedFactory.error(
                "Player Not Found",
                "That osu! player doesn't exist."
            )

            await interaction.followup.send(embed=embed)
            return

        connection = sqlite3.connect("database/bot.db")
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                interaction.user.id,
                user["id"],
                user["username"],

                user["statistics"]["pp"],
                user["statistics"]["global_rank"],
                user["statistics"]["country_rank"],
                user["statistics"]["hit_accuracy"],

                user["avatar_url"],
                user["country_code"]
            )
        )       

        connection.commit()
        connection.close()

        embed = EmbedFactory.success(
            "Account Linked",
            (
                f"Discord: {interaction.user.mention}\n"
                f"osu!: **{user['username']}**"
            )
        )

        await interaction.followup.send(embed=embed)

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="profile",
        description="View an osu! profile."
    )
    async def profile(
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
            await refresh_player(osu_id)

            user = await OsuAPI.get_user(username)

            if user is None:
                embed = EmbedFactory.error(
                    "Player Not Found",
                    "That osu! player doesn't exist."
                )

                await interaction.followup.send(embed=embed)
                return

            osu_id = user["id"]

        user = await OsuAPI.get_user_by_id(osu_id)

        await refresh_player(osu_id)

        if user is None:
            embed = EmbedFactory.error(
                "Player Not Found",
                "Couldn't retrieve that osu! profile."
            )

            await interaction.followup.send(embed=embed)
            return

        embed = OsuEmbed.profile(user)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Profile(bot))