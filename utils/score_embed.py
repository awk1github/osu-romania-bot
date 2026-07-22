from __future__ import annotations

from datetime import datetime
from typing import Any

import discord

from utils.emojis import RANK_EMOJIS
from utils.osu_score import format_mods, miss_count, played_at, score_value


class ScoreEmbed:
    @staticmethod
    def _number(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _format_length(seconds: Any) -> str:
        total_seconds = max(0, ScoreEmbed._number(seconds))
        minutes, remaining = divmod(total_seconds, 60)
        return f"{minutes}:{remaining:02d}"

    @staticmethod
    def recent(score: dict[str, Any]) -> discord.Embed:
        beatmap = score.get("beatmap") or {}
        beatmapset = score.get("beatmapset") or {}
        user = score.get("user") or {}
        pp = (
            f"{score['pp']:.2f}pp"
            if score.get("pp") is not None
            else "Unranked"
        )
        mod_acronyms = []

        for mod in score.get("mods", []):
            if isinstance(mod, str):
                mod_acronyms.append(mod.upper())
            elif isinstance(mod, dict):
                acronym = mod.get("acronym")

                if acronym:
                    mod_acronyms.append(acronym.upper())

        has_classic = "CL" in mod_acronyms

        if has_classic:
            displayed_score = (
                score.get("legacy_total_score")
                or score.get("classic_total_score")
                or score.get("total_score")
                or 0
            )
        else:
            displayed_score = (
                score.get("total_score")
                or score.get("classic_total_score")
                or score.get("legacy_total_score")
                or 0
            )

        global_rank = score.get("rank_global")

   
        user_stats = user.get("statistics") or {}

        global_rank = user_stats.get("global_rank")

        country_rank = user_stats.get("country_rank")
        country_code = user.get("country_code") or "?"
        
        mods = format_mods(score)
        misses = miss_count(score)
        rank = str(score.get("rank") or "F").upper()
        rank_emoji = RANK_EMOJIS.get(rank, rank)

        combo = ScoreEmbed._number(
            score.get("max_combo") or score.get("maximum_combo")
        )
        map_max_combo = beatmap.get("max_combo")

        if map_max_combo is None:
            combo_text = f"**{combo:,}x**"
        else:
            combo_text = (
                f"**{combo:,}x**/{ScoreEmbed._number(map_max_combo):,}x"
            )

        total_length = beatmap.get("total_length") or beatmap.get("hit_length")
        length = ScoreEmbed._format_length(total_length)

        cs = ScoreEmbed._float(beatmap.get("cs"))
        ar = ScoreEmbed._float(beatmap.get("ar"))
        od = ScoreEmbed._float(beatmap.get("accuracy"))
        hp = ScoreEmbed._float(beatmap.get("drain"))
        bpm = ScoreEmbed._float(beatmap.get("bpm"))

        mapper = beatmapset.get("creator") or "Unknown mapper"

        ranked_date_raw = (
            beatmapset.get("ranked_date")
            or beatmap.get("last_updated")
        )

        ranked_date = "Unknown date"

        if ranked_date_raw:
            try:
                ranked_date_dt = datetime.fromisoformat(
                    str(ranked_date_raw).replace("Z", "+00:00")
                )

                ranked_date = ranked_date_dt.strftime(
                    "%Y-%m-%d %H:%M UTC"
                )
            except (ValueError, TypeError):
                pass

        pp_value = score.get("pp")
        pp_text = (
            f"{ScoreEmbed._float(pp_value):.2f}pp"
            if pp_value is not None
            else "Unranked"
        )

        accuracy = ScoreEmbed._float(score.get("accuracy")) * 100
        time_value = played_at(score)
        time_ago = (
            discord.utils.format_dt(time_value, style="R")
            if time_value is not None
            else "Unknown time"
        )

        global_text = f"#{int(global_rank):,}" if global_rank else "N/A"
        country_text = (
            f"{country_code} #{int(country_rank):,}"
            if country_rank
            else country_code
        )

        artist = beatmapset.get("artist") or "Unknown artist"
        title = beatmapset.get("title") or "Unknown title"
        version = beatmap.get("version") or "Unknown difficulty"
        stars = ScoreEmbed._float(beatmap.get("difficulty_rating"))

        beatmap_id = beatmap.get("id") or score.get("beatmap_id")
        beatmap_url = beatmap.get("url")
        if not beatmap_url and beatmap_id is not None:
            beatmap_url = f"https://osu.ppy.sh/beatmaps/{beatmap_id}"

        embed = discord.Embed(
            url=beatmap_url,
            color=discord.Color.purple(),
        )

        map_title = f"{artist} - {title} [{version}] • {stars:.2f}★"

        if beatmap_url:
            map_title = f"[{map_title}]({beatmap_url})"

        embed.description = (
            f"**{map_title}**\n"
            f"{rank_emoji} **{mods}** • **{pp_text}** • "
            f"**{accuracy:.2f}%** • {time_ago}\n"
            f"**{ScoreEmbed._number(displayed_score):,}** • "
            f"{combo_text} • **{misses}❌**\n"
            f"`{length}` • CS `{cs:g}` • AR `{ar:g}` • "
            f"OD `{od:g}` • HP `{hp:g}` • **{bpm:g} BPM**"
        )

        username = user.get("username") or "Unknown player"
        user_id = user.get("id") or score.get("user_id")
        avatar_url = user.get("avatar_url")

        embed.set_author(
            name=f"{username} • {global_text} • {country_text}",
            icon_url=avatar_url or None,
            url=(
                f"https://osu.ppy.sh/users/{user_id}"
                if user_id is not None
                else None
            ),
        )

        covers = beatmapset.get("covers") or {}
        cover_url = (
            covers.get("cover@2x")
            or covers.get("cover")
            or covers.get("card@2x")
            or covers.get("card")
        )
        if cover_url:
            embed.set_image(url=cover_url)


        embed.set_footer(text=f"Mapped by {mapper} • Ranked {ranked_date}")
        return embed

    @staticmethod
    def top(user: dict[str, Any], scores: list[dict[str, Any]]) -> discord.Embed:
        username = user.get("username") or "Unknown player"
        user_id = user.get("id")

        embed = discord.Embed(
            title=f"🏆 {username}'s Top Plays",
            url=(
                f"https://osu.ppy.sh/users/{user_id}"
                if user_id is not None
                else None
            ),
            color=discord.Color.gold(),
        )

        avatar_url = user.get("avatar_url")
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        stats = user.get("statistics") or {}
        global_rank = stats.get("global_rank")
        country_rank = stats.get("country_rank")
        pp = stats.get("pp")

        profile_lines = []
        if global_rank is not None:
            profile_lines.append(f"🌍 **Global:** #{int(global_rank):,}")
        if country_rank is not None:
            profile_lines.append(f"🇷🇴 **Country:** #{int(country_rank):,}")
        if pp is not None:
            profile_lines.append(f"💎 **PP:** {float(pp):,.0f}pp")

        embed.description = "\n".join(profile_lines) or None

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

        for index, score in enumerate(scores[:5]):
            beatmap = score.get("beatmap") or {}
            beatmapset = score.get("beatmapset") or {}

            mods = format_mods(score)
            mod_text = "" if mods == "NM" else f" +{mods}"
            misses = miss_count(score)

            artist = beatmapset.get("artist") or "Unknown artist"
            title = beatmapset.get("title") or "Unknown title"
            version = beatmap.get("version") or "Unknown difficulty"
            stars = ScoreEmbed._float(beatmap.get("difficulty_rating"))
            beatmap_id = beatmap.get("id") or score.get("beatmap_id")
            beatmap_url = beatmap.get("url")

            if not beatmap_url and beatmap_id is not None:
                beatmap_url = f"https://osu.ppy.sh/beatmaps/{beatmap_id}"

            map_label = (
                f"{artist} - {title} [{version}] ({stars:.2f}★){mod_text}"
            )
            map_title = (
                f"[{map_label}]({beatmap_url})" if beatmap_url else map_label
            )

            score_pp = score.get("pp")
            pp_text = (
                f"{ScoreEmbed._float(score_pp):.2f}pp"
                if score_pp is not None
                else "Unranked"
            )
            accuracy = ScoreEmbed._float(score.get("accuracy")) * 100
            combo = ScoreEmbed._number(
                score.get("max_combo") or score.get("maximum_combo")
            )
            rank = str(score.get("rank") or "?").upper()

            embed.add_field(
                name=medals[index],
                value=(
                    f"{map_title}\n"
                    f"💎 **{pp_text}**\n"
                    f"🎯 **{accuracy:.2f}%** • 🏅 **{rank}**\n"
                    f"🔥 **{combo:,}x** • ❌ **{misses}**"
                ),
                inline=False,
            )

        embed.set_footer(text="osu!Romania • Top Plays")
        return embed
