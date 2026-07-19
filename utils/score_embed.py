import discord
from datetime import datetime, timezone


class ScoreEmbed:

    @staticmethod
    def recent(score: dict) -> discord.Embed:

        beatmap = score["beatmap"]
        beatmapset = score["beatmapset"]
        user = score["user"]

        mods = "".join(score["mods"]) if score["mods"] else "NM"

        misses = score["statistics"]["count_miss"]

        pp = (
            f"{score['pp']:.2f}pp"
            if score.get("pp") is not None
            else "Unranked"
        )

        max_combo = beatmap.get("max_combo", "?")

        created = datetime.fromisoformat(
            score["created_at"].replace("Z", "+00:00")
        )

        seconds = int(
            (datetime.now(timezone.utc) - created).total_seconds()
        )

        if seconds < 60:
            played = f"{seconds}s ago"
        elif seconds < 3600:
            played = f"{seconds // 60}m ago"
        elif seconds < 86400:
            played = f"{seconds // 3600}h ago"
        else:
            played = f"{seconds // 86400}d ago"

        embed = discord.Embed(
            title=f"{beatmapset['artist']} - {beatmapset['title']}",
            url=beatmap["url"],
            description=f"**Difficulty:** {beatmap['version']}",
            color=discord.Color.purple()
        )

        embed.set_author(
            name=user["username"],
            icon_url=user["avatar_url"],
            url=f"https://osu.ppy.sh/users/{user['id']}"
        )

        embed.set_thumbnail(
            url=beatmapset["covers"]["cover"]
        )

        embed.add_field(
            name="🏆 Result",
            value=(
                f"**Rank:** {score['rank']}\n"
                f"**PP:** {pp}\n"
                f"**Accuracy:** {score['accuracy']*100:.2f}%"
            ),
            inline=True
        )

        embed.add_field(
            name="🎮 Gameplay",
            value=(
                f"**Combo:** {score['max_combo']}x / {max_combo}x\n"
                f"**Misses:** {misses}\n"
                f"**Mods:** {mods}"
            ),
            inline=True
        )

        embed.add_field(
            name="🗺️ Beatmap",
            value=(
                f"**Stars:** ⭐ {beatmap['difficulty_rating']:.2f}\n"
                f"**Length:** {beatmap['hit_length']//60}:{beatmap['hit_length']%60:02d}\n"
                f"**BPM:** {beatmap['bpm']}"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Difficulty",
            value=(
                f"**AR:** {beatmap['ar']}\n"
                f"**CS:** {beatmap['cs']}\n"
                f"**OD:** {beatmap['accuracy']}\n"
                f"**HP:** {beatmap['drain']}"
            ),
            inline=True
        )

        embed.add_field(
            name="🕒 Played",
            value=played,
            inline=True
        )

        embed.set_footer(
            text="osu!Romania • Recent Play"
        )


    @staticmethod
    def top(user: dict, scores: list) -> discord.Embed:

        embed = discord.Embed(
            title=f"🏆 {user['username']}'s Top Plays",
            url=f"https://osu.ppy.sh/users/{user['id']}",
            color=discord.Color.gold()
        )

        embed.set_thumbnail(
            url=user["avatar_url"]
        )

        stats = user["statistics"]

        embed.description = (
            f"🌍 **Global:** #{stats['global_rank']:,}\n"
            f"🇷🇴 **Country:** #{stats['country_rank']:,}\n"
            f"💎 **PP:** {stats['pp']:,.0f}pp"
        )

        medals = [
            "🥇",
            "🥈",
            "🥉",
            "4️⃣",
            "5️⃣"
        ]

        for i, score in enumerate(scores[:5]):

            beatmap = score["beatmap"]
            beatmapset = score["beatmapset"]

            mods = "".join(score["mods"])
            if not mods:
                mods = "NM"

            misses = score["statistics"]["count_miss"]

            mods = "".join(score["mods"]) if score["mods"] else "NM"
            mod_text = "" if mods == "NM" else f" +{mods}"

            misses = score["statistics"]["count_miss"]
        
            map_title = (
                f"[{beatmapset['artist']} - {beatmapset['title']} "
                f"[{beatmap['version']}]{mod_text}]"
                f"({beatmap['url']})"
            )

            embed.add_field(
                name=f"{medals[i]}",
                value=(
                    f"{map_title}\n"
                    f"💎 **{score['pp']:.2f}pp**\n"
                    f"⭐ **{beatmap['difficulty_rating']:.2f}★** • "
                    f"🎯 **{score['accuracy']*100:.2f}%** • "
                    f"🏅 **{score['rank']}**\n"
                    f"🔥 **{score['max_combo']}x** • "
                    f"❌ **{misses}**\n"
                    f"\u200b"
                ),
                inline=False
            )

        embed.set_footer(
            text="osu!Romania • Top Plays"
        )

        return embed