import discord

from discord.ext import commands
from discord import app_commands

from utils.osu_embed import OsuEmbed

from utils.osu_api import OsuAPI


class Osu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="osu",
        description="Look up an osu! player."
    )
    async def osu(
        self,
        interaction: discord.Interaction,
        username: str
    ):
        await interaction.response.defer()

        user = await OsuAPI.get_user(username)

        if user is None:
            await interaction.followup.send(
                "❌ Player not found."
            )
            return

        embed = OsuEmbed.profile(user)

        await interaction.followup.send(embed=embed)



async def setup(bot):
    await bot.add_cog(Osu(bot))