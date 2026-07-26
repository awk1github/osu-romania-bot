import discord
from datetime import datetime, UTC


class OsuEmbed:

    @staticmethod
    def profile(
        user: dict,
        county=None,
    ) -> discord.Embed:

        stats = user.get("statistics") or {}

        def format_rank(value) -> str:
            if value is None:
                return "Unranked"

            return f"#{value:,}"

        def country_code_to_flag(
            country_code: str | None,
        ) -> str:
            if not country_code or len(country_code) != 2:
                return "🌐"

            return "".join(
                chr(ord(character) + 127397)
                for character in country_code.upper()
            )

        pp = stats.get("pp") or 0
        accuracy = stats.get("hit_accuracy") or 0
        play_count = stats.get("play_count") or 0
        play_time = stats.get("play_time") or 0
        ranked_score = stats.get("ranked_score") or 0
        total_score = stats.get("total_score") or 0

        level_data = stats.get("level") or {}
        level = level_data.get("current", 0)
        level_progress = level_data.get("progress", 0)

        global_rank = format_rank(
            stats.get("global_rank")
        )

        country_rank = format_rank(
            stats.get("country_rank")
        )

        country_code = (
            user.get("country_code")
            or (user.get("country") or {}).get("code")
        )

        country_name = (
            (user.get("country") or {}).get("name")
            or country_code
            or "Country"
        )

        country_flag = country_code_to_flag(
            country_code
        )

        county_line = "📍 County: Not assigned"

        if county is not None:
            try:
                county_name = county["county_name"]
                county_rank = format_rank(
                    county["county_rank"]
                )

                county_line = (
                    f"📍 {county_name}: {county_rank}"
                )
            except (KeyError, TypeError, IndexError):
                pass

        joined_datetime = None

        join_date = user.get("join_date")

        if join_date:
            try:
                joined_datetime = datetime.fromisoformat(
                    join_date.replace("Z", "+00:00")
                ).astimezone(UTC)
            except ValueError:
                pass

        is_online = user.get("is_online", False)
        last_visit = user.get("last_visit")

        if is_online:
            activity_text = "🟢 Online"
        elif last_visit:
            last_visit_datetime = discord.utils.parse_time(
                last_visit
            )

            if last_visit_datetime:
                activity_text = (
                    "Last seen\n"
                    f"{discord.utils.format_dt(last_visit_datetime, style='R')}"
                )
            else:
                activity_text = "🔴 Offline"
        else:
            activity_text = "🔴 Offline"

        embed = discord.Embed(
            title=user["username"],
            url=(
                f"https://osu.ppy.sh/users/"
                f"{user['id']}"
            ),
            description=(
                f"💎 **{pp:,.0f}pp** • "
                f"⭐ **Level {level} "
                f"({level_progress}%)**"
            ),
            color=discord.Color.from_rgb(
                255,
                102,
                170,
            ),
        )

        # First row: Rankings and Performance
        embed.add_field(
            name="📊 Rankings",
            value=(
                f"🌍 Global: **{global_rank}**\n"
                f"{country_flag} {country_name}: "
                f"**{country_rank}**\n"
                f"{county_line}"
            ),
            inline=True,
        )

        embed.add_field(
            name="🎯 Performance",
            value=(
                f"Accuracy: **{accuracy:.2f}%**\n"
                f"Plays: **{play_count:,}**\n"
                f"Play Time: **{play_time // 3600:,}h**"
            ),
            inline=True,
        )

        embed.add_field(
            name="🏆 Scores",
            value=(
                f"Ranked: **{ranked_score:,}**\n"
                f"Total: **{total_score:,}**"
            ),
            inline=True,
        )

        avatar_url = user.get("avatar_url")

        if avatar_url:
            embed.set_thumbnail(
                url=avatar_url
            )

        if joined_datetime:
            footer_text = (
                f"osu!Romania • "
                f"Joined {discord.utils.format_dt(joined_datetime, style='D')} • "
                f"osu! ID: {user['id']}"
            )
        else:
            footer_text = (
                f"osu!Romania • "
                f"osu! ID: {user['id']}"
            )

        embed.set_footer(text=footer_text)

        return embed