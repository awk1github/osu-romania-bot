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
            parts = content.split(maxsplit=1)

            username = parts[1] if len(parts) > 1 else None

            await self.handle_recent(
                message,
                username,
            )

        elif content.startswith("<c"):
            parts = content.split(maxsplit=1)

            username = parts[1] if len(parts) > 1 else None

            await self.handle_compare(
                message,
                username,
            )
            
        async def handle_recent(
            self,
            message: discord.Message,
            username: str | None,
        ) -> None:
            await message.reply(
                f"Recent for: {username or 'linked account'}",
                mention_author=False,
            )


        async def handle_compare(
            self,
            message: discord.Message,
            username: str | None,
        ) -> None:
            await message.reply(
                f"Compare for: {username or 'linked account'}",
                mention_author=False,
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCommands(bot))