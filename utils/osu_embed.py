import discord


class OsuEmbed:

    @staticmethod
    def profile(
        user: dict,
        county= None,
    ) -> discord.Embed:

        stats = user["statistics"]

        global_rank = (
            f"#{stats['global_rank']:,}"
            if stats["global_rank"] is not None
            else "Unranked"
        )

        country_rank = (
            f"#{stats['country_rank']:,}"
            if stats["country_rank"] is not None
            else "Unranked"
        )

        embed = discord.Embed(
            title=f"🎵 {user['username']}",
            url=f"https://osu.ppy.sh/users/{user['id']}",
            color=discord.Color.pink()
        )

        embed.set_thumbnail(url=user["avatar_url"])

        cover = user.get("cover_url")
        if cover:
            embed.set_image(url=cover)

        embed.add_field(
            name="⭐ Performance",
            value=(
                f"**PP:** {stats['pp']:,.0f}\n"
                f"**Accuracy:** {stats['hit_accuracy']:.2f}%\n"
                f"**Level:** {stats['level']['current']}"
            ),
            inline=True
        )

        embed.add_field(
            name="🏆 Rankings",
            value=(
                f"**Global:** {global_rank}\n"
                f"**Country:** {country_rank}"
            ),
            inline=True
        )

        embed.add_field(
            name="🎮 Activity",
            value=(
                f"**Play Count:** {stats['play_count']:,}\n"
                f"**Play Time:** {stats['play_time'] // 3600:,} hours"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Scores",
            value=(
                f"**Ranked:** {stats['ranked_score']:,}\n"
                f"**Total:** {stats['total_score']:,}"
            ),
            inline=True
        )

        location = f"{user['country']['name']} ({user['country_code']})"

        if county:
            county_name = county["county_name"]
            county_rank = county["county_rank"]

            location += f"\n📍 {county_name}"

            if county_rank is not None:
                location += f" — #{county_rank:,} in county"

        embed.add_field(
            name="🌍 Location",
            value=location,
            inline=True
        )

        embed.add_field(
            name="📅 Joined",
            value=user["join_date"][:10],
            inline=True
        )

        embed.set_footer(
            text=f"osu! ID: {user['id']}"
        )

        return embed