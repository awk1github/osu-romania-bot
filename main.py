from dotenv import load_dotenv
import os
import asyncio

import discord
from discord.ext import commands
from discord import app_commands
from utils.oauth_server import OAuthServer

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1473125019692564542

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class OsuRomania(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        print("Loading extensions...")

        extensions = [
            "cogs.moderation",
            "cogs.achievements",
            "cogs.server_settings",
            "cogs.county",
            "cogs.help",
            "cogs.osu.profile",
            "cogs.osu.scores",
            "cogs.osu.leaderboard",
            "cogs.osu.listeners",
        ]

        for extension in extensions:
            await self.load_extension(extension)
            print(f"✓ Loaded {extension}")

        await OAuthServer.start(self)

        guild = discord.Object(id=GUILD_ID)

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        print("-" * 40)
        print(f"Logged in as {self.user}")
        print(f"Application ID: {self.application_id}")
        print(f"Guilds: {len(self.guilds)}")
        print(f"Cogs Loaded: {len(self.cogs)}")
        print("-" * 40)


bot = OsuRomania()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):

        message = "❌ You don't have permission to use this command."

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )

        return

    raise error


async def main():
    async with bot:
        await bot.start(TOKEN)


asyncio.run(main())