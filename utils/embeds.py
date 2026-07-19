import discord
from datetime import datetime


class EmbedFactory:

    BOT_NAME = "osu!Romania"

    @staticmethod
    def _create(
        emoji: str,
        color: discord.Color,
        title: str,
        description: str = ""
    ) -> discord.Embed:

        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )

        embed.set_footer(text=EmbedFactory.BOT_NAME)

        return embed

    @staticmethod
    def success(
        title: str,
        description: str = ""
    ) -> discord.Embed:

        return EmbedFactory._create(
            "✅",
            discord.Color.green(),
            title,
            description
        )

    @staticmethod
    def error(
        title: str,
        description: str = ""
    ) -> discord.Embed:

        return EmbedFactory._create(
            "❌",
            discord.Color.red(),
            title,
            description
        )

    @staticmethod
    def warning(
        title: str,
        description: str = ""
    ) -> discord.Embed:

        return EmbedFactory._create(
            "⚠️",
            discord.Color.orange(),
            title,
            description
        )

    @staticmethod
    def info(
        title: str,
        description: str = ""
    ) -> discord.Embed:

        return EmbedFactory._create(
            "ℹ️",
            discord.Color.blue(),
            title,
            description
        )