import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="View the list of available commands."
    )
    async def help(
        self,
        interaction: discord.Interaction
    ) -> None:

        embed = discord.Embed(
            title="📖 osu!Romania Commands",
            description=(
                "Everything you need to use the osu!Romania Discord bot."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🔗 Account",
            value=(
                "`/link` — Link your osu! account\n"
                "`/unlink` — Remove your linked account"
            ),
            inline=False
        )

        embed.add_field(
            name="👤 Profiles",
            value=(
                "`/profile` — View your linked profile\n"
                "`/profile username:<player>` — View any osu! player\n"
                "`/profile member:<member>` — View a linked Discord member"
                "`/recent` — View your most recent play\n"
                "`/recent username:<player>` — View another player's recent play\n"
                "`/top` — View your best osu! plays\n"
                "`/top username:<player>` — View another player's top plays"
            ),
            inline=False
        )

        embed.add_field(
            name="🏆 Leaderboards",
            value=(
                "`/leaderboard` — View the server osu! leaderboard\n"
                "`/county leaderboard:<county>` — View each county osu! leaderboard\n"
                "Use the command options to filter the rankings when available."
            ),
            inline=False
        )

        embed.add_field(
            name="🗺️ Beatmaps",
            value=(
                "Post any osu! beatmap link in chat and the bot will "
                "automatically display map information and the server leaderboard."
            ),
            inline=False
        )

        embed.add_field(
            name="🇷🇴 Romania Features",
            value=(
                "• County information\n"
                "• County rankings\n"
                "• Automatic rank roles"
            ),
            inline=False
        )

        embed.set_footer(
            text="More commands will be added over time."
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))