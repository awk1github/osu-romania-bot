from __future__ import annotations

import re
import sqlite3
from typing import Any

import discord
from discord.ext import commands

from utils.embeds import EmbedFactory
from utils.emojis import RANK_EMOJIS
from utils.osu_api import OsuAPI
from utils.osu_score import format_mods
from utils.score_embed import ScoreEmbed


DATABASE_PATH = "database/bot.db"

BEATMAP_REGEX = re.compile(
    r"https?://osu\.ppy\.sh/"
    r"(?:beatmaps/(\d+)|beatmapsets/\d+#(?:osu|taiko|fruits|mania)/(\d+))",
    re.IGNORECASE,
)


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

        if not content:
            return

        command, _, argument = content.partition(" ")
        command = command.lower()
        username = argument.strip() or None

        if command == "<rs":
            await self.handle_recent(
                message=message,
                username=username,
            )
            return

        if command == "<c":
            await self.handle_compare(
                message=message,
                username=username,
            )

    async def resolve_osu_user(
        self,
        discord_user_id: int,
        username: str | None,
    ) -> tuple[int | None, dict[str, Any] | None, discord.Embed | None]:
        if username is not None:
            profile = await OsuAPI.get_user(username)

            if profile is None:
                return (
                    None,
                    None,
                    EmbedFactory.error(
                        "Player Not Found",
                        "That osu! player doesn't exist.",
                    ),
                )

            await OsuAPI.close_session()
            return int(profile["id"]), profile, None

        with sqlite3.connect(DATABASE_PATH) as connection:
            row = connection.execute(
                """
                SELECT osu_id
                FROM osu_accounts
                WHERE discord_id = ?
                """,
                (discord_user_id,),
            ).fetchone()

        if row is None:
            return (
                None,
                None,
                EmbedFactory.error(
                    "Account Not Linked",
                    "Use `/link` first or specify an osu! username.",
                ),
            )

        osu_id = int(row[0])
        profile = await OsuAPI.get_user(osu_id)

        if profile is None:
            return (
                None,
                None,
                EmbedFactory.error(
                    "Player Error",
                    "The linked osu! profile could not be loaded.",
                ),
            )

        await OsuAPI.close_session()
        return osu_id, profile, None

    async def handle_recent(
        self,
        message: discord.Message,
        username: str | None,
    ) -> None:
        async with message.channel.typing():
            try:
                osu_id, profile, error_embed = await self.resolve_osu_user(
                    discord_user_id=message.author.id,
                    username=username,
                )

                if error_embed is not None:
                    await message.reply(
                        embed=error_embed,
                        mention_author=False,
                    )
                    return

                if osu_id is None or profile is None:
                    return

                score = await OsuAPI.get_recent(osu_id)

                if score is None:
                    await message.reply(
                        embed=EmbedFactory.info(
                            "No Recent Score",
                            "No recent plays were found.",
                        ),
                        mention_author=False,
                    )
                    return

                mod_acronyms: list[str] = []

                for mod in score.get("mods", []):
                    if isinstance(mod, str):
                        mod_acronyms.append(mod.upper())
                    elif isinstance(mod, dict):
                        acronym = mod.get("acronym")

                        if acronym:
                            mod_acronyms.append(str(acronym).upper())

                if "CL" in mod_acronyms:
                    legacy_score_id = score.get("legacy_score_id")

                    if legacy_score_id is not None:
                        full_score = await OsuAPI.get_legacy_score(
                            int(legacy_score_id),
                            mode="osu",
                        )
                    else:
                        full_score = None
                else:
                    score_id = score.get("id")

                    if score_id is not None:
                        full_score = await OsuAPI.get_score(
                            int(score_id),
                            ruleset="osu",
                        )
                    else:
                        full_score = None

                if full_score is not None:
                    score = full_score

                score["user"] = profile

                if not score.get("beatmap") or not score.get("beatmapset"):
                    score = await OsuAPI.enrich_score(
                        score,
                        include_user=False,
                        include_beatmap=True,
                        include_beatmapset=True,
                    )
                    score["user"] = profile

                embed = ScoreEmbed.recent(score)

                await OsuAPI.close_session()
                await message.reply(
                    embed=embed,
                    mention_author=False,
                )

            except Exception as error:
                print(f"Error in <rs: {error!r}")

                await message.reply(
                    embed=EmbedFactory.error(
                        "Recent Score Error",
                        "Something went wrong while loading the recent score.",
                    ),
                    mention_author=False,
                )

    async def handle_compare(
        self,
        message: discord.Message,
        username: str | None,
    ) -> None:
        reference = message.reference

        if reference is None or reference.message_id is None:
            await message.reply(
                embed=EmbedFactory.info(
                    "Reply Required",
                    "Reply to a message containing an osu! beatmap link, "
                    "then use `<c` or `<c username>`.",
                ),
                mention_author=False,
            )
            return

        async with message.channel.typing():
            try:
                replied_message = await self.get_replied_message(message)

                if replied_message is None:
                    await message.reply(
                        embed=EmbedFactory.error(
                            "Message Unavailable",
                            "I couldn't read the message you replied to.",
                        ),
                        mention_author=False,
                    )
                    return

                beatmap_id = self.extract_beatmap_id(replied_message)

                if beatmap_id is None:
                    await message.reply(
                        embed=EmbedFactory.info(
                            "Beatmap Not Found",
                            "The replied message doesn't contain a supported "
                            "osu! beatmap link.",
                        ),
                        mention_author=False,
                    )
                    return

                osu_id, profile, error_embed = await self.resolve_osu_user(
                    discord_user_id=message.author.id,
                    username=username,
                )

                if error_embed is not None:
                    await message.reply(
                        embed=error_embed,
                        mention_author=False,
                    )
                    return

                if osu_id is None or profile is None:
                    return

                response = await OsuAPI.api_get(
                    f"beatmaps/{beatmap_id}/scores/users/{osu_id}/all",
                    params={
                        "ruleset": "osu",
                        "legacy_only": 0,
                    },
                )

                scores = self.extract_scores(response)

                if not scores:
                    await message.reply(
                        embed=EmbedFactory.info(
                            "No Scores",
                            f"**{profile['username']}** has no submitted "
                            "scores on that beatmap.",
                        ),
                        mention_author=False,
                    )
                    return

                scores.sort(
                    key=self.score_sort_value,
                    reverse=True,
                )

                embed = self.build_compare_embed(
                    profile=profile,
                    beatmap_id=beatmap_id,
                    scores=scores,
                )

                await OsuAPI.close_session()
                await message.reply(
                    embed=embed,
                    mention_author=False,
                )

            except Exception as error:
                print(f"Error in <c: {error!r}")

                await message.reply(
                    embed=EmbedFactory.error(
                        "Compare Error",
                        "Something went wrong while loading the beatmap scores.",
                    ),
                    mention_author=False,
                )

    async def get_replied_message(
        self,
        message: discord.Message,
    ) -> discord.Message | None:
        reference = message.reference

        if reference is None or reference.message_id is None:
            return None

        if isinstance(reference.resolved, discord.Message):
            return reference.resolved

        try:
            return await message.channel.fetch_message(reference.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    @staticmethod
    def extract_beatmap_id(
        message: discord.Message,
    ) -> int | None:
        searchable_text: list[str] = [message.content or ""]

        for embed in message.embeds:
            if embed.url:
                searchable_text.append(embed.url)

            if embed.title:
                searchable_text.append(embed.title)

            if embed.description:
                searchable_text.append(embed.description)

            if embed.author and embed.author.url:
                searchable_text.append(embed.author.url)

            for field in embed.fields:
                searchable_text.append(field.name or "")
                searchable_text.append(field.value or "")

        for text in searchable_text:
            match = BEATMAP_REGEX.search(text)

            if match:
                beatmap_id = match.group(1) or match.group(2)
                return int(beatmap_id)

        return None

    @staticmethod
    def extract_scores(
        response: Any,
    ) -> list[dict[str, Any]]:
        if isinstance(response, list):
            return [score for score in response if isinstance(score, dict)]

        if not isinstance(response, dict):
            return []

        scores = response.get("scores")

        if isinstance(scores, list):
            return [score for score in scores if isinstance(score, dict)]

        score = response.get("score")

        if isinstance(score, dict):
            return [score]

        return []

    @staticmethod
    def score_sort_value(
        score: dict[str, Any],
    ) -> tuple[float, float, int]:
        pp = score.get("pp")
        accuracy = score.get("accuracy")
        total_score = (
            score.get("total_score")
            or score.get("classic_total_score")
            or score.get("legacy_total_score")
            or score.get("score")
            or 0
        )

        try:
            pp_value = float(pp) if pp is not None else -1.0
        except (TypeError, ValueError):
            pp_value = -1.0

        try:
            accuracy_value = float(accuracy or 0)
        except (TypeError, ValueError):
            accuracy_value = 0.0

        try:
            total_score_value = int(total_score)
        except (TypeError, ValueError):
            total_score_value = 0

        return pp_value, accuracy_value, total_score_value

    @staticmethod
    def build_compare_embed(
        profile: dict[str, Any],
        beatmap_id: int,
        scores: list[dict[str, Any]],
    ) -> discord.Embed:
        username = profile.get("username") or "Unknown player"
        user_id = profile.get("id")
        avatar_url = profile.get("avatar_url")

        lines: list[str] = []

        for index, score in enumerate(scores, start=1):
            if index == 1:
                placement = "🥇"
            elif index == 2:
                placement = "🥈"
            elif index == 3:
                placement = "🥉"
            else:
                placement = f"**#{index}**"

            rank = str(score.get("rank") or "F").upper()
            rank_emoji = RANK_EMOJIS.get(rank, f"`{rank}`")
            mods = format_mods(score)

            pp = score.get("pp")

            try:
                pp_text = f"{float(pp):.2f}pp" if pp is not None else "Unranked"
            except (TypeError, ValueError):
                pp_text = "Unranked"

            try:
                accuracy = float(score.get("accuracy") or 0) * 100
            except (TypeError, ValueError):
                accuracy = 0.0

            total_score = (
                score.get("total_score")
                or score.get("classic_total_score")
                or score.get("legacy_total_score")
                or score.get("score")
                or 0
            )

            try:
                score_text = f"{int(total_score):,}"
            except (TypeError, ValueError):
                score_text = "0"

            lines.append(
                f"{placement} {rank_emoji} **{mods}** • "
                f"**{pp_text}** • **{accuracy:.2f}%** • "
                f"**{score_text}**"
            )

        embed = discord.Embed(
            title=(
                f"{username} • {len(scores)} "
                f"{'score' if len(scores) == 1 else 'scores'}"
            ),
            url=f"https://osu.ppy.sh/beatmaps/{beatmap_id}",
            description="\n".join(lines),
            color=discord.Color.purple(),
        )

        embed.set_author(
            name=username,
            icon_url=avatar_url or None,
            url=(
                f"https://osu.ppy.sh/users/{user_id}"
                if user_id is not None
                else None
            ),
        )

        embed.set_footer(text=f"osu!Romania • Beatmap {beatmap_id}")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatCommands(bot))