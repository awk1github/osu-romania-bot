import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


DATABASE_PATH = Path(__file__).resolve().parent.parent / "database" / "bot.db"


class AchievementSettings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="achievementchannel",
        description="Set the channel used for achievement announcements.",
    )
    @app_commands.describe(
        channel="The channel where achievements should be posted."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def achievement_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO guild_settings (
                    guild_id,
                    achievement_channel_id,
                    achievements_enabled
                )
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id) DO UPDATE SET
                    achievement_channel_id = excluded.achievement_channel_id
                """,
                (
                    interaction.guild.id,
                    channel.id,
                ),
            )

            connection.commit()

        await interaction.response.send_message(
            f"Achievement announcements will now be posted in {channel.mention}.",
            ephemeral=True,
        )

    @achievement_channel.error
    async def achievement_channel_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need the Administrator permission to use this command.",
                ephemeral=True,
            )
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AchievementSettings(bot))