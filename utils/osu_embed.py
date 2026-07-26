import discord


class OsuEmbed:

    @staticmethod
    def profile(
        user: dict,
        county=None,
    ) -> discord.Embed:

        stats = user.get("statistics") or {}

        def format_rank(value):
            return f"#{value:,}" if value is not None else "Unranked"

        pp = stats.get("pp") or 0
        accuracy = stats.get("hit_accuracy") or 0
        play_count = stats.get("play_count") or 0
        play_time = stats.get("play_time") or 0

        level_data = stats.get("level") or {}
        level = level_data.get("current", 0)

        global_rank = format_rank(stats.get("global_rank"))
        country_rank = format_rank(stats.get("country_rank"))

        county_text = None

        if county is not None:
            try:
                county_name = county["county_name"]
                county_rank = county["county_rank"]

                county_text = (
                    f"📍 **{county_name} {format_rank(county_rank)}**"
                )
            except (KeyError, TypeError, IndexError):
                county_text = None

        ranking_parts = [
            f"🌍 **{global_rank}**",
            f"🇷🇴 **{country_rank}**",
        ]

        if county_text:
            ranking_parts.append(county_text)

        embed = discord.Embed(
            title=user["username"],
            url=f"https://osu.ppy.sh/users/{user['id']}",
            description=(
                f"💎 **{pp:,.0f}pp** • "
                + " • ".join(ranking_parts)
                + "\n\n"
                f"🎯 **{accuracy:.2f}%** • "
                f"⭐ **Lv. {level}** • "
                f"🎮 **{play_count:,} plays** • "
                f"⏱️ **{play_time // 3600:,}h**"
            ),
            color=discord.Color.from_rgb(255, 102, 170),
        )

        avatar_url = user.get("avatar_url")

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.set_footer(
            text=f"osu!Romania • osu! ID: {user['id']}"
        )

        return embed