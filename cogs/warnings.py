import discord
import sqlite3

from discord.ext import commands
from discord import app_commands
from datetime import datetime

from utils.embeds import EmbedFactory


class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="warn",
        description="Warn a member."
    )
    @app_commands.default_permissions(moderate_members=True)

    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        await interaction.response.defer()

        connection = sqlite3.connect("database/bot.db")
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO warnings
            (user_id, moderator_id, reason, date)
            VALUES (?, ?, ?, ?)
            """,
            (
                member.id,
                interaction.user.id,
                reason,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        connection.commit()
        connection.close()

        embed = EmbedFactory.success(
            "Member Warned",
            f"{member.mention} has been warned.\n\nReason: **{reason}**"
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="warnings",
        description="View a member's warnings."
    )

    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        await interaction.response.defer()

        connection = sqlite3.connect("database/bot.db")
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, moderator_id, reason, date
            FROM warnings
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (member.id,)
    )

        rows = cursor.fetchall()

        connection.close()

        if not rows:
            embed = EmbedFactory.info(
                "No Warnings",
                f"{member.mention} has no warnings."
            )

            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            color=discord.Color.orange()
        )

        for warn_id, moderator_id, reason, date in rows:
            embed.add_field(
                name=f"Warning #{warn_id}",
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Moderator ID:** {moderator_id}\n"
                    f"**Date:** {date}"
                ),
                inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="removewarn",
        description="Remove a warning by its ID."
    )
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def removewarn(
        self,
        interaction: discord.Interaction,
        warning_id: int
    ):
        await interaction.response.defer()

        connection = sqlite3.connect("database/bot.db")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM warnings WHERE id = ?",
            (warning_id,)
        )

        warning = cursor.fetchone()

        if warning is None:
            connection.close()

            embed = EmbedFactory.error(
                "Warning Not Found",
                f"No warning with ID **{warning_id}** exists."
            )

            await interaction.followup.send(embed=embed)
            return

        cursor.execute(
            "DELETE FROM warnings WHERE id = ?",
            (warning_id,)
        )

        connection.commit()
        connection.close()

        embed = EmbedFactory.success(
            "Warning Removed",
            f"Warning **#{warning_id}** has been removed."
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="clearwarnings",
        description="Remove all warnings from a member."
    )
    @app_commands.default_permissions(moderate_members=True)
    
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        await interaction.response.defer()

        connection = sqlite3.connect("database/bot.db")
        cursor = connection.cursor()

    # Count the user's warnings first
        cursor.execute(
            "SELECT COUNT(*) FROM warnings WHERE user_id = ?",
            (member.id,)
    )

        count = cursor.fetchone()[0]

        if count == 0:
            connection.close()

            embed = EmbedFactory.info(
                "No Warnings",
                f"{member.mention} has no warnings to remove."
        )

            await interaction.followup.send(embed=embed)
            return

    # Delete all warnings
        cursor.execute(
            "DELETE FROM warnings WHERE user_id = ?",
            (member.id,)
    )

        connection.commit()
        connection.close()

        embed = EmbedFactory.success(
            "Warnings Cleared",
            f"Removed **{count}** warning(s) from {member.mention}."
    )

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Warnings(bot))