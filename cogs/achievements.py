import asyncio
import json
import logging
import sqlite3

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from utils.osu_api import OsuAPI
from utils.osu_score import format_mods, score_url

import discord
from discord.ext import commands, tasks
from discord import app_commands


DATABASE_PATH = Path(__file__).resolve().parent.parent / "database" / "bot.db"

CHECK_INTERVAL_MINUTES = 15
REQUEST_DELAY_SECONDS = 1

PLAY_PP_MILESTONES = (
    100,
    200,
    300,
    400,
    500,
    600,
    700,
    800,
    900,
    1000,
    1100,
    1200,
)

TOTAL_PP_MILESTONES = (
    1_000,
    2_500,
    5_000,
    7_500,
    10_000,
    12_500,
    15_000,
    17_500,
    20_000,
    25_000,
    30_000,
)

GLOBAL_RANK_MILESTONES = (
    100_000,
    50_000,
    25_000,
    10_000,
    5_000,
    2_500,
    1_000,
    500,
    250,
    100,
    50,
    10,
    1,
)

COUNTRY_RANK_MILESTONES = (
    1_000,
    500,
    250,
    100,
    50,
    25,
    10,
    5,
    3,
    1,
)

logger = logging.getLogger(__name__)


@dataclass
class LinkedUser:
    discord_id: int
    osu_id: int
    osu_username: str


@dataclass
class Snapshot:
    osu_id: int
    total_pp: float | None
    global_rank: int | None
    country_rank: int | None
    top_score_id: int | None
    top_score_pp: float | None
    top_10_ids: list[int]


@dataclass
class Achievement:
    event_type: str
    event_key: str
    embed: discord.Embed


class Achievements(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_achievements.start()

    def cog_unload(self) -> None:
        self.check_achievements.cancel()

    async def fetch_profile(self, osu_id: int) -> dict[str, Any]:
        return await OsuAPI.get_user(osu_id)

    async def fetch_top_10(self, osu_id: int) -> list[dict[str, Any]]:
        return await OsuAPI.get_top(osu_id, limit=5)
    
    def build_test_achievement_embed(
        self,
        member: discord.Member,
    ) -> discord.Embed:
        embed = discord.Embed(
            title="🔥 New Top 5 Play!",
            description=(
                f"**{member.display_name}** set a new **#2 top play**!\n\n"
                "[**Camellia — Exit This Earth's Atomosphere "
                "[Evolution]**](https://osu.ppy.sh/beatmaps/1234567)"
            ),
            color=discord.Color.from_rgb(255, 102, 170),
            timestamp=discord.utils.utcnow(),
        )

        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url,
        )

        embed.set_thumbnail(
            url=member.display_avatar.url,
        )

        embed.add_field(
            name="Performance",
            value="**412.56pp**",
            inline=True,
        )

        embed.add_field(
            name="Accuracy",
            value="**98.72%**",
            inline=True,
        )

        embed.add_field(
            name="Top Play",
            value="**#2**",
            inline=True,
        )

        embed.add_field(
            name="Grade",
            value="**S**",
            inline=True,
        )

        embed.add_field(
            name="Mods",
            value="**+HDHR**",
            inline=True,
        )

        embed.add_field(
            name="Combo",
            value="**1,234x**",
            inline=True,
        )

        embed.add_field(
            name="✨ PP Milestone",
            value="First play above **400pp**!",
            inline=False,
        )

        embed.add_field(
            name="Profile Progress",
            value=(
                "**Total PP:** 12,483.42pp → 12,511.86pp\n"
                "**Global Rank:** #8,242 → #8,105\n"
                "**Romania Rank:** #84 → #81"
            ),
            inline=False,
        )

        embed.set_image(
            url="https://assets.ppy.sh/beatmaps/1234567/covers/cover.jpg"
        )

        embed.add_field(
            name="\u200b",
            value=(
                "[View score](https://osu.ppy.sh/scores/1234567890)"
                " • "
                "[View beatmap](https://osu.ppy.sh/beatmaps/1234567)"
            ),
            inline=False,
        )

        embed.set_footer(
            text="osu!Romania Achievements • Test announcement"
        )   

        return embed
    
    @app_commands.checks.has_permissions(administrator=True)
    async def test_achievement(
            self,
            interaction: discord.Interaction,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        channel_id = await asyncio.to_thread(
            self.get_guild_achievement_channel,
            interaction.guild.id,
        )

        if channel_id is None:
            await interaction.followup.send(
                "No achievement channel is configured. Use "
                "`/achievementchannel` first.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(channel_id)

        if channel is None:
            try:
                channel = await interaction.guild.fetch_channel(channel_id)
            except discord.NotFound:
                await interaction.followup.send(
                    "The configured achievement channel no longer exists.",
                    ephemeral=True,
                )
                return
            except discord.Forbidden:
                await interaction.followup.send(
                    "I cannot access the configured achievement channel.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException:
                await interaction.followup.send(
                    "Discord returned an error while finding the channel.",
                    ephemeral=True,
                )
                return

        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                "The configured achievement channel is not a text channel.",
                ephemeral=True,
            )
            return

        if isinstance(interaction.user, discord.Member):
            member = interaction.user
        else:
            member = interaction.guild.me

        if member is None:
            await interaction.followup.send(
                "I could not build the test achievement.",
                ephemeral=True,
            )
            return

        embed = self.build_test_achievement_embed(member)

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send(
                f"I do not have permission to send embeds in {channel.mention}.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "Discord returned an error while sending the test.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Test achievement sent to {channel.mention}.",
            ephemeral=True,
        )

    def get_guild_achievement_channel(
        self,
        guild_id: int,
    ) -> int | None:
        with sqlite3.connect(DATABASE_PATH) as connection:
            row = connection.execute(
                """
                SELECT achievement_channel_id
                FROM guild_settings
                WHERE guild_id = ?
                AND achievements_enabled = 1
                AND achievement_channel_id IS NOT NULL
                """,
                (guild_id,),
            ).fetchone()

        if row is None:
            return None

        return int(row[0])

    # ------------------------------------------------------------------
    # Main background loop
    # ------------------------------------------------------------------

    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def check_achievements(self) -> None:
        linked_users = await asyncio.to_thread(self.get_linked_users)

        if not linked_users:
            return

        logger.info(
            "Checking achievements for %s linked users.",
            len(linked_users),
        )

        for linked_user in linked_users:
            try:
                await self.check_user(linked_user)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Failed to check achievements for osu! user %s.",
                    linked_user.osu_id,
                )

            await asyncio.sleep(REQUEST_DELAY_SECONDS)

    @check_achievements.before_loop
    async def before_check_achievements(self) -> None:
        await self.bot.wait_until_ready()

    @check_achievements.error
    async def achievement_loop_error(self, error: Exception) -> None:
        logger.exception(
            "Achievement background loop failed.",
            exc_info=error,
        )

    async def check_user(self, linked_user: LinkedUser) -> None:
        profile, top_scores = await asyncio.gather(
            self.fetch_profile(linked_user.osu_id),
            self.fetch_top_10(linked_user.osu_id),
        )

        if not profile:
            logger.warning(
                "No profile returned for osu! user %s.",
                linked_user.osu_id,
            )
            return

        if top_scores is None:
            top_scores = []

        current_snapshot = self.build_snapshot(
            osu_id=linked_user.osu_id,
            profile=profile,
            top_scores=top_scores,
        )

        previous_snapshot = await asyncio.to_thread(
            self.get_snapshot,
            linked_user.osu_id,
        )

        # First scan is silent. It only stores the current state.
        if previous_snapshot is None:
            await asyncio.to_thread(
                self.save_snapshot,
                current_snapshot,
            )

            logger.info(
                "Created initial achievement snapshot for %s.",
                linked_user.osu_username,
            )
            return

        achievements = self.detect_achievements(
            linked_user=linked_user,
            profile=profile,
            top_scores=top_scores,
            old=previous_snapshot,
            new=current_snapshot,
        )

        for achievement in achievements:
            was_created = await asyncio.to_thread(
                self.register_event,
                linked_user.osu_id,
                achievement.event_type,
                achievement.event_key,
            )

            if not was_created:
                continue

            await self.send_achievement(
                discord_id=linked_user.discord_id,
                embed=achievement.embed,
            )

        await asyncio.to_thread(
            self.save_snapshot,
            current_snapshot,
        )

    # ------------------------------------------------------------------
    # Achievement detection
    # ------------------------------------------------------------------

    def detect_achievements(
        self,
        linked_user: LinkedUser,
        profile: dict[str, Any],
        top_scores: list[dict[str, Any]],
        old: Snapshot,
        new: Snapshot,
    ) -> list[Achievement]:
        achievements: list[Achievement] = []

        achievements.extend(
            self.detect_new_top_plays(
                linked_user=linked_user,
                profile=profile,
                top_scores=top_scores,
                old=old,
                new=new,
            )
        )

        achievements.extend(
            self.detect_total_pp_milestones(
                linked_user=linked_user,
                profile=profile,
                old=old,
                new=new,
            )
        )

        achievements.extend(
            self.detect_rank_milestones(
                linked_user=linked_user,
                profile=profile,
                old=old,
                new=new,
            )
        )

        return achievements

    def detect_new_top_plays(
        self,
        linked_user: LinkedUser,
        profile: dict[str, Any],
        top_scores: list[dict[str, Any]],
        old: Snapshot,
        new: Snapshot,
    ) -> list[Achievement]:
        achievements: list[Achievement] = []
        old_score_ids = set(old.top_10_ids)

        for position, score in enumerate(top_scores[:5], start=1):
            score_id = self.to_int(score.get("id"))

            if score_id is None or score_id in old_score_ids:
                continue

            score_pp = self.to_float(score.get("pp")) or 0
            crossed_milestones = self.get_crossed_increasing_milestones(
                old_value=old.top_score_pp,
                new_value=score_pp,
                milestones=PLAY_PP_MILESTONES,
            )

            embed = self.build_score_embed(
                linked_user=linked_user,
                profile=profile,
                score=score,
                position=position,
                pp_milestones=crossed_milestones,
                old_snapshot=old,
                new_snapshot=new,
            )

            achievements.append(
                Achievement(
                    event_type="top10_score",
                    event_key=f"score:{score_id}",
                    embed=embed,
                )
            )

        return achievements

    def detect_total_pp_milestones(
        self,
        linked_user: LinkedUser,
        profile: dict[str, Any],
        old: Snapshot,
        new: Snapshot,
    ) -> list[Achievement]:
        milestones = self.get_crossed_increasing_milestones(
            old_value=old.total_pp,
            new_value=new.total_pp,
            milestones=TOTAL_PP_MILESTONES,
        )

        achievements: list[Achievement] = []

        for milestone in milestones:
            embed = self.base_player_embed(
                linked_user=linked_user,
                profile=profile,
                title="🎉 Total PP Milestone!",
                description=(
                    f"**{linked_user.osu_username}** reached "
                    f"**{milestone:,}pp**!"
                ),
            )

            if new.total_pp is not None:
                embed.add_field(
                    name="Current Performance",
                    value=f"**{new.total_pp:,.2f}pp**",
                    inline=True,
                )

            achievements.append(
                Achievement(
                    event_type="total_pp",
                    event_key=f"total_pp:{milestone}",
                    embed=embed,
                )
            )

        return achievements

    def detect_rank_milestones(
        self,
        linked_user: LinkedUser,
        profile: dict[str, Any],
        old: Snapshot,
        new: Snapshot,
    ) -> list[Achievement]:
        achievements: list[Achievement] = []

        global_milestones = self.get_crossed_rank_milestones(
            old_rank=old.global_rank,
            new_rank=new.global_rank,
            milestones=GLOBAL_RANK_MILESTONES,
        )

        for milestone in global_milestones:
            embed = self.base_player_embed(
                linked_user=linked_user,
                profile=profile,
                title="🌍 Global Rank Milestone!",
                description=(
                    f"**{linked_user.osu_username}** entered the global "
                    f"**Top {milestone:,}**!"
                ),
            )

            if new.global_rank is not None:
                embed.add_field(
                    name="Current Global Rank",
                    value=f"**#{new.global_rank:,}**",
                    inline=True,
                )

            achievements.append(
                Achievement(
                    event_type="global_rank",
                    event_key=f"global_rank:{milestone}",
                    embed=embed,
                )
            )

        country_milestones = self.get_crossed_rank_milestones(
            old_rank=old.country_rank,
            new_rank=new.country_rank,
            milestones=COUNTRY_RANK_MILESTONES,
        )

        for milestone in country_milestones:
            embed = self.base_player_embed(
                linked_user=linked_user,
                profile=profile,
                title="🇷🇴 Romania Rank Milestone!",
                description=(
                    f"**{linked_user.osu_username}** entered Romania's "
                    f"**Top {milestone:,}**!"
                ),
            )

            if new.country_rank is not None:
                embed.add_field(
                    name="Current Romania Rank",
                    value=f"**#{new.country_rank:,}**",
                    inline=True,
                )

            achievements.append(
                Achievement(
                    event_type="country_rank",
                    event_key=f"country_rank:{milestone}",
                    embed=embed,
                )
            )

        return achievements

    # ------------------------------------------------------------------
    # Embeds
    # ------------------------------------------------------------------

    def build_score_embed(
        self,
        linked_user: LinkedUser,
        profile: dict[str, Any],
        score: dict[str, Any],
        position: int,
        pp_milestones: list[int],
        old_snapshot: Snapshot,
        new_snapshot: Snapshot,
    ) -> discord.Embed:
        beatmap = score.get("beatmap") or {}
        beatmapset = score.get("beatmapset") or {}

        artist = beatmapset.get("artist") or "Unknown artist"
        title = beatmapset.get("title") or "Unknown title"
        version = beatmap.get("version") or "Unknown difficulty"

        score_id = self.to_int(score.get("id"))
        beatmap_id = self.to_int(beatmap.get("id"))

        score_pp = self.to_float(score.get("pp"))
        accuracy = self.to_float(score.get("accuracy"))
        max_combo = self.to_int(score.get("max_combo"))

        grade = score.get("rank") or "?"
        mods = format_mods(score)

        username = profile.get("username") or linked_user.osu_username
        avatar_url = profile.get("avatar_url")

        if position == 1:
            embed_title = "👑 New Personal Best!"
            description_start = (
                f"**{username}** set a new **#1 top play**!\n\n"
            )
        else:
            embed_title = "🔥 New Top 5 Play!"
            description_start = (
                f"**{username}** set a new **#{position} top play**!\n\n"
            )

        if beatmap_id is not None:
            beatmap_text = (
                f"[**{artist} — {title} [{version}]**]"
                f"(https://osu.ppy.sh/beatmaps/{beatmap_id})"
            )
        else:
            beatmap_text = f"**{artist} — {title} [{version}]**"

        embed = discord.Embed(
            title=embed_title,
            description=description_start + beatmap_text,
            color=discord.Color.from_rgb(255, 102, 170),
            timestamp=discord.utils.utcnow(),
        )

        embed.set_author(
            name=username,
            url=f"https://osu.ppy.sh/users/{linked_user.osu_id}",
            icon_url=avatar_url or None,
        )

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.add_field(
            name="Performance",
            value=(
                f"**{score_pp:.2f}pp**"
                if score_pp is not None
                else "**Unknown**"
            ),
            inline=True,
            )

        embed.add_field(
            name="Accuracy",
            value=(
                f"**{accuracy * 100:.2f}%**"
                if accuracy is not None
                else "**Unknown**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Top Play",
            value=f"**#{position}**",
            inline=True,
        )

        embed.add_field(
            name="Grade",
            value=f"**{grade}**",
            inline=True,
        )

        embed.add_field(
            name="Mods",
            value=f"**{mods}**",
            inline=True,
        )

        embed.add_field(
            name="Combo",
            value=(
                f"**{max_combo:,}x**"
                if max_combo is not None
                else "**Unknown**"
            ),
            inline=True,
        )

        if pp_milestones:
            milestone_text = ", ".join(
                f"**{milestone}pp**"
                for milestone in pp_milestones
            )

            embed.add_field(
                name="✨ PP Milestone",
                value=f"First play above {milestone_text}!",
                inline=False,
            )

        progress_lines: list[str] = []

        if (
            old_snapshot.total_pp is not None
            and new_snapshot.total_pp is not None
        ):
            pp_difference = new_snapshot.total_pp - old_snapshot.total_pp

            progress_lines.append(
                f"**Total PP:** "
                f"{old_snapshot.total_pp:,.2f}pp → "
                f"{new_snapshot.total_pp:,.2f}pp "
                f"({pp_difference:+,.2f}pp)"
            )

        if (
            old_snapshot.global_rank is not None
            and new_snapshot.global_rank is not None
        ):
            rank_difference = (
                old_snapshot.global_rank - new_snapshot.global_rank
            )

            progress_lines.append(
                f"**Global Rank:** "
                f"#{old_snapshot.global_rank:,} → "
                f"#{new_snapshot.global_rank:,} "
                f"({rank_difference:+,})"
            )

        if (
            old_snapshot.country_rank is not None
            and new_snapshot.country_rank is not None
        ):
            country_difference = (
                old_snapshot.country_rank - new_snapshot.country_rank
            )

            progress_lines.append(
                f"**Romania Rank:** "
                f"#{old_snapshot.country_rank:,} → "
                f"#{new_snapshot.country_rank:,} "
                f"({country_difference:+,})"
            )

        if progress_lines:
            embed.add_field(
                name="Profile Progress",
                value="\n".join(progress_lines),
                inline=False,
            )

        covers = beatmapset.get("covers") or {}

        cover_url = (
            covers.get("cover")
            or covers.get("cover@2x")
            or covers.get("card")
            or covers.get("card@2x")
        )

        if cover_url:
            embed.set_image(url=cover_url)

        links: list[str] = []

        play_url = score_url(score)

        if play_url is not None:
            links.append(f"[View score]({play_url})")

        if beatmap_id is not None:
            links.append(
                f"[View beatmap](https://osu.ppy.sh/beatmaps/{beatmap_id})"
            )

        links.append(
            f"[View profile](https://osu.ppy.sh/users/{linked_user.osu_id})"
        )

        embed.add_field(
            name="\u200b",
            value=" • ".join(links),
            inline=False,
        )

        embed.set_footer(
            text=(
                f"osu!Romania Achievements • "
                f"osu! ID: {linked_user.osu_id}"
            )
        )

        return embed

    def base_player_embed(
        self,
        linked_user: LinkedUser,
        profile: dict[str, Any],
        title: str,
        description: str,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple(),
        )

        avatar_url = profile.get("avatar_url")

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.set_footer(
            text=f"osu!Romania • osu! ID: {linked_user.osu_id}"
        )

        return embed

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_achievement(
        self,
        discord_id: int,
        embed: discord.Embed,
    ) -> None:
        channel_settings = await asyncio.to_thread(
            self.get_achievement_channels
        )

        for guild_id, channel_id in channel_settings:
            guild = self.bot.get_guild(guild_id)

            if guild is None:
                continue

            # Only announce in servers where this linked Discord user exists.
            member = guild.get_member(discord_id)

            if member is None:
                try:
                    member = await guild.fetch_member(discord_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue

            channel = guild.get_channel(channel_id)

            if channel is None:
                try:
                    fetched_channel = await self.bot.fetch_channel(channel_id)
                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    continue

                channel = fetched_channel

            if not isinstance(channel, discord.TextChannel):
                continue

            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(
                    "Missing permission to post achievements in channel %s.",
                    channel_id,
                )
            except discord.HTTPException:
                logger.exception(
                    "Failed to send achievement in channel %s.",
                    channel_id,
                )

    # ------------------------------------------------------------------
    # Snapshot handling
    # ------------------------------------------------------------------

    def build_snapshot(
        self,
        osu_id: int,
        profile: dict[str, Any],
        top_scores: list[dict[str, Any]],
    ) -> Snapshot:
        statistics = profile.get("statistics") or {}

        top_score = top_scores[0] if top_scores else {}

        top_10_ids = [
            score_id
            for score in top_scores[:5]
            if (score_id := self.to_int(score.get("id"))) is not None
        ]

        return Snapshot(
            osu_id=osu_id,
            total_pp=self.to_float(statistics.get("pp")),
            global_rank=self.to_int(statistics.get("global_rank")),
            country_rank=self.to_int(statistics.get("country_rank")),
            top_score_id=self.to_int(top_score.get("id")),
            top_score_pp=self.to_float(top_score.get("pp")),
            top_10_ids=top_10_ids,
        )

    def get_snapshot(self, osu_id: int) -> Snapshot | None:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row

            row = connection.execute(
                """
                SELECT
                    osu_id,
                    total_pp,
                    global_rank,
                    country_rank,
                    top_score_id,
                    top_score_pp,
                    top_10_json
                FROM achievement_snapshots
                WHERE osu_id = ?
                """,
                (osu_id,),
            ).fetchone()

        if row is None:
            return None

        try:
            top_10_ids = json.loads(row["top_10_json"])
        except (TypeError, json.JSONDecodeError):
            top_10_ids = []

        return Snapshot(
            osu_id=row["osu_id"],
            total_pp=row["total_pp"],
            global_rank=row["global_rank"],
            country_rank=row["country_rank"],
            top_score_id=row["top_score_id"],
            top_score_pp=row["top_score_pp"],
            top_10_ids=[
                score_id
                for value in top_10_ids
                if (score_id := self.to_int(value)) is not None
            ],
        )

    def save_snapshot(self, snapshot: Snapshot) -> None:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(
                """
                INSERT INTO achievement_snapshots (
                    osu_id,
                    total_pp,
                    global_rank,
                    country_rank,
                    top_score_id,
                    top_score_pp,
                    top_10_json,
                    initialized,
                    last_checked
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(osu_id) DO UPDATE SET
                    total_pp = excluded.total_pp,
                    global_rank = excluded.global_rank,
                    country_rank = excluded.country_rank,
                    top_score_id = excluded.top_score_id,
                    top_score_pp = excluded.top_score_pp,
                    top_10_json = excluded.top_10_json,
                    initialized = 1,
                    last_checked = CURRENT_TIMESTAMP
                """,
                (
                    snapshot.osu_id,
                    snapshot.total_pp,
                    snapshot.global_rank,
                    snapshot.country_rank,
                    snapshot.top_score_id,
                    snapshot.top_score_pp,
                    json.dumps(snapshot.top_10_ids),
                ),
            )

            connection.commit()

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def get_linked_users(self) -> list[LinkedUser]:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row

            rows = connection.execute(
                """
                SELECT
                    discord_id,
                    osu_id,
                    osu_username
                FROM osu_accounts
                WHERE achievements_enabled = 1
                """
            ).fetchall()

        return [
            LinkedUser(
                discord_id=row["discord_id"],
                osu_id=row["osu_id"],
                osu_username=row["osu_username"],
            )
            for row in rows
        ]

    def get_achievement_channels(self) -> list[tuple[int, int]]:
        with sqlite3.connect(DATABASE_PATH) as connection:
            rows = connection.execute(
                """
                SELECT
                    guild_id,
                    achievement_channel_id
                FROM guild_settings
                WHERE achievements_enabled = 1
                  AND achievement_channel_id IS NOT NULL
                """
            ).fetchall()

        return [
            (int(guild_id), int(channel_id))
            for guild_id, channel_id in rows
        ]

    def register_event(
        self,
        osu_id: int,
        event_type: str,
        event_key: str,
    ) -> bool:
        try:
            with sqlite3.connect(DATABASE_PATH) as connection:
                connection.execute(
                    """
                    INSERT INTO achievement_events (
                        osu_id,
                        event_type,
                        event_key
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        osu_id,
                        event_type,
                        f"{osu_id}:{event_key}",
                    ),
                )

                connection.commit()

            return True

        except sqlite3.IntegrityError:
            return False

    # ------------------------------------------------------------------
    # Comparison helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_crossed_increasing_milestones(
        old_value: float | None,
        new_value: float | None,
        milestones: tuple[int, ...],
    ) -> list[int]:
        if old_value is None or new_value is None:
            return []

        if new_value <= old_value:
            return []

        return [
            milestone
            for milestone in milestones
            if old_value < milestone <= new_value
        ]

    @staticmethod
    def get_crossed_rank_milestones(
        old_rank: int | None,
        new_rank: int | None,
        milestones: tuple[int, ...],
    ) -> list[int]:
        if old_rank is None or new_rank is None:
            return []

        if new_rank >= old_rank:
            return []

        return [
            milestone
            for milestone in milestones
            if old_rank > milestone >= new_rank
        ]

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_mods(mods: Any) -> str:
        if not mods:
            return "NM"

        formatted_mods: list[str] = []

        for mod in mods:
            if isinstance(mod, str):
                formatted_mods.append(mod)
                continue

            if isinstance(mod, dict):
                acronym = mod.get("acronym")

                if acronym:
                    formatted_mods.append(str(acronym))

        if not formatted_mods:
            return "NM"

        return f"+{''.join(formatted_mods)}"

    @staticmethod
    def to_int(value: Any) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def to_float(value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Achievements(bot))