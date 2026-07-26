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
        if message.author.bot:
            return

        content = message.content.strip()

        # Separate the command from the optional username.
        command, _, argument = content.partition(" ")
        username = argument.strip() or None

        if command.lower() == "<rs":
            await self.handle_recent(
                message=message,
                username=username,
            )
            return

        if command.lower() == "<c":
            await self.handle_compare(
                message=message,
                username=username,
            )

    async def handle_recent(
        self,
        message: discord.Message,
        username: str | None,
    ) -> None:
        await message.reply(
            f"Recent for: **{username or 'linked account'}**",
            mention_author=False,
        )

    async def handle_compare(
        self,
        message: discord.Message,
        username: str | None,
    ) -> None:
        await message.reply(
            f"Compare for: **{username or 'linked account'}**",
            mention_author=False,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatCommands(bot))