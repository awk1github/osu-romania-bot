import re

import discord
from discord.ext import commands

from utils.beatmap_embed import BeatmapEmbed
from utils.osu_api import OsuAPI


BEATMAP_REGEX = re.compile(
    r"https?://osu\.ppy\.sh/(?:beatmaps/(\d+)|beatmapsets/\d+#osu/(\d+))"
)


class Listeners(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages sent by bots
        if message.author.bot:
            return

        print(f"Message detected: {message.content}")

        match = BEATMAP_REGEX.search(message.content)

        print(f"Regex match: {match}")

        if not match:
            return

        beatmap_id = match.group(1) or match.group(2)

        print(f"Beatmap ID: {beatmap_id}")

        try:
            beatmap = await OsuAPI.get_beatmap(beatmap_id)

        except Exception as error:
            print(
                f"Beatmap API error: "
                f"{type(error).__name__}: {error}"
            )
            return

        await OsuAPI.close_session()
        if beatmap is None:
            print("Beatmap API returned no data.")
            return

        try:
            embed = BeatmapEmbed.create(
                beatmap=beatmap,
            )

        except Exception as error:
            print(
                f"Beatmap embed error: "
                f"{type(error).__name__}: {error}"
            )
            return

        try:
            await message.reply(
                embed=embed,
                mention_author=False
            )

        except discord.Forbidden:
            print(
                "The bot does not have permission to send "
                "messages or embeds in this channel."
            )

        except discord.HTTPException as error:
            print(f"Discord reply error: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Listeners(bot))