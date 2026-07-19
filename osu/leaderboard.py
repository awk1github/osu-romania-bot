import sqlite3
import discord

from discord.ext import commands
from discord import app_commands

from utils.embeds import EmbedFactory


class Leaderboard(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description="View the osu!Romania server leaderboard."
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer()

        connection = sqlite3.connect("database/bot.db")
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                discord_id,
                osu_username,
                pp,
                global_rank,
                country_rank,
                accuracy,
                country_code
            FROM osu_accounts
            WHERE pp IS NOT NULL
            ORDER BY pp DESC
            LIMIT 10
        """)

        players = cursor.fetchall()
        connection.close()

        if not players:
            embed = EmbedFactory.info(
                "Leaderboard Empty",
                "Nobody has linked their osu! account yet."
            )

            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🏆 osu!Romania Leaderboard",
            description="Top linked players in this Discord server",
            color=discord.Color.gold()
        )

        medals = [
            "🥇",
            "🥈",
            "🥉",
            "4️⃣",
            "5️⃣",
            "6️⃣",
            "7️⃣",
            "8️⃣",
            "9️⃣",
            "🔟"
        ]

        description = ""

        for i, player in enumerate(players):

            (
                discord_id,
                username,
                pp,
                global_rank,
                country_rank,
                accuracy,
                country_code
            ) = player

            you = " ⭐" if discord_id == interaction.user.id else ""

            global_text = (
                f"#{global_rank:,}"
                if global_rank is not None
                else "Unranked"
            )

            country_text = (
                f"#{country_rank:,}"
                if country_rank is not None
                else "Unranked"
            )

            description += (
                f"{medals[i]} **{username}**{you}\n"
                f"💎 **{pp:,.0f}pp** • "
                f"🌍 **{global_text}** • "
                f"🇷🇴 **{country_text}** • "
                f"🎯 **{accuracy:.2f}%**\n\n"
            )

        embed.description = description

        embed.set_footer(
            text="⭐ = You • osu!Romania"
        )

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))