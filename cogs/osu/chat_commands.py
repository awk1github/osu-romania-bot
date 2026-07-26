import discord
from discord.ext import commands


class ChatCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ) -> None:
        # Ignore bots
        if message.author.bot:
            return

        content = message.content.strip()

        if content.startswith("<rs"):
            await message.reply(
                "Recent command detected.",
                mention_author=False,
            )

        elif content.startswith("<c"):
            await message.reply(
                "Compare command detected.",
                mention_author=False,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCommands(bot))