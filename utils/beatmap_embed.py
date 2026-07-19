import discord


class BeatmapEmbed:
    STATUS_EMOJIS = {
        "ranked": "🟢",
        "approved": "🟣",
        "qualified": "🟡",
        "loved": "💙",
        "pending": "⚪",
        "wip": "🟠",
        "graveyard": "⚫",
    }

    @staticmethod
    def get_color(stars: float) -> discord.Color:
        if stars < 2:
            return discord.Color.light_grey()

        if stars < 3:
            return discord.Color.green()

        if stars < 4:
            return discord.Color.teal()

        if stars < 5:
            return discord.Color.blue()

        if stars < 6:
            return discord.Color.purple()

        if stars < 7:
            return discord.Color.magenta()

        return discord.Color.red()

    @staticmethod
    def format_length(seconds: int | float | None) -> str:
        try:
            total_seconds = int(seconds or 0)
        except (TypeError, ValueError):
            total_seconds = 0

        minutes, remaining_seconds = divmod(total_seconds, 60)

        return f"{minutes}:{remaining_seconds:02d}"

    @staticmethod
    def format_number(value) -> str:
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "N/A"

    @staticmethod
    def format_stat(value) -> str:
        try:
            number = float(value)

            if number.is_integer():
                return str(int(number))

            return f"{number:.1f}"

        except (TypeError, ValueError):
            return "N/A"

    @staticmethod
    def format_accuracy(score: dict) -> str:
        accuracy = score.get("accuracy")

        if accuracy is None:
            return "N/A"

        try:
            accuracy = float(accuracy)
        except (TypeError, ValueError):
            return "N/A"

        if accuracy <= 1:
            accuracy *= 100

        return f"{accuracy:.2f}%"

    @staticmethod
    def format_mods(score: dict) -> str:
        mods = score.get("mods") or []

        if not mods:
            return "NM"

        formatted_mods = []

        for mod in mods:
            if isinstance(mod, str):
                formatted_mods.append(mod)

            elif isinstance(mod, dict):
                acronym = mod.get("acronym")

                if acronym:
                    formatted_mods.append(acronym)

        return "".join(formatted_mods) or "NM"

    @staticmethod
    def get_score_username(score: dict) -> str:
        user = score.get("user") or {}

        return (
            user.get("username")
            or score.get("_linked_osu_username")
            or "Unknown player"
        )

    @staticmethod
    def get_score_value(score: dict) -> int:
        value = (
            score.get("total_score")
            or score.get("legacy_total_score")
            or score.get("score")
            or 0
        )

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def format_status(status: str | None) -> str:
        raw_status = str(status or "unknown").lower()
        emoji = BeatmapEmbed.STATUS_EMOJIS.get(raw_status, "❔")
        label = raw_status.replace("_", " ").title()

        return f"{emoji} {label}"

    @staticmethod
    def create(
        beatmap: dict,
        server_records: list[dict] | None = None
    ) -> discord.Embed:
        beatmapset = beatmap.get("beatmapset") or {}

        beatmap_id = beatmap.get("id")
        beatmapset_id = beatmap.get("beatmapset_id")

        artist = beatmapset.get("artist", "Unknown artist")
        title = beatmapset.get("title", "Unknown title")
        version = beatmap.get("version", "Unknown difficulty")
        creator = beatmapset.get("creator", "Unknown mapper")

        try:
            stars = float(
                beatmap.get("difficulty_rating") or 0
            )
        except (TypeError, ValueError):
            stars = 0

        beatmap_url = beatmap.get("url")

        if not beatmap_url and beatmap_id:
            beatmap_url = (
                f"https://osu.ppy.sh/beatmaps/{beatmap_id}"
            )

        status = BeatmapEmbed.format_status(
            beatmap.get("status")
        )

        embed = discord.Embed(
            title=(
                f"★{stars:.2f} • "
                f"{artist} - {title} [{version}]"
            ),
            url=beatmap_url,
            description=f"Mapped by **{creator}** • {status}",
            color=BeatmapEmbed.get_color(stars)
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

        mapper_user = beatmapset.get("user") or {}
        mapper_avatar = mapper_user.get("avatar_url")

        if mapper_avatar:
            embed.set_thumbnail(url=mapper_avatar)

        ar = BeatmapEmbed.format_stat(
            beatmap.get("ar")
        )

        od = BeatmapEmbed.format_stat(
            beatmap.get("accuracy")
        )

        cs = BeatmapEmbed.format_stat(
            beatmap.get("cs")
        )

        hp = BeatmapEmbed.format_stat(
            beatmap.get("drain")
        )

        embed.add_field(
            name="⭐ Difficulty",
            value=(
                f"`AR {ar}`  `OD {od}`\n"
                f"`CS {cs}`  `HP {hp}`"
            ),
            inline=True
        )

        hit_length = BeatmapEmbed.format_length(
            beatmap.get("hit_length")
        )

        bpm = BeatmapEmbed.format_stat(
            beatmap.get("bpm")
        )

        max_combo = beatmap.get("max_combo")

        if max_combo is None:
            max_combo_text = "N/A"
        else:
            max_combo_text = (
                f"{BeatmapEmbed.format_number(max_combo)}x"
            )

        embed.add_field(
            name="🎵 Map",
            value=(
                f"**Length:** {hit_length}\n"
                f"**BPM:** {bpm}\n"
                f"**Combo:** {max_combo_text}"
            ),
            inline=True
        )

        playcount = beatmap.get("playcount") or 0
        favourite_count = (
            beatmapset.get("favourite_count") or 0
        )

        mode = str(
            beatmap.get("mode") or "osu"
        ).upper()

        embed.add_field(
            name="📈 Statistics",
            value=(
                f"**Plays:** "
                f"{BeatmapEmbed.format_number(playcount)}\n"
                f"**Favourites:** "
                f"{BeatmapEmbed.format_number(favourite_count)}\n"
                f"**Mode:** {mode}"
            ),
            inline=True
        )

        # Invisible spacer field.
        # Discord usually trims blank lines at the beginning
        # of normal field values, so this creates real spacing.

        if server_records:
            medals = ["🥇", "🥈", "🥉"]
            leaderboard_entries = []

            for index, score in enumerate(
                server_records[:3]
            ):
                username = (
                    BeatmapEmbed.get_score_username(score)
                )

                osu_id = (
                    score.get("user_id")
                    or score.get("_linked_osu_id")
                )

                if osu_id:
                    username_display = (
                        f"[**{username}**]"
                        f"(https://osu.ppy.sh/users/{osu_id})"
                    )
                else:
                    username_display = f"**{username}**"

                rank = str(
                    score.get("rank") or "?"
                ).upper()

                mods = BeatmapEmbed.format_mods(score)

                accuracy = (
                    BeatmapEmbed.format_accuracy(score)
                )

                total_score = (
                    BeatmapEmbed.get_score_value(score)
                )

                combo = (
                    score.get("max_combo")
                    or score.get("maximum_combo")
                )

                pp = score.get("pp")

                first_line = (
                    f"{medals[index]} {username_display}"
                )

                score_details = [
                    f"**{rank}**",
                    f"`+{mods}`",
                    f"**{accuracy}**"
                ]

                if pp is not None:
                    try:
                        score_details.append(
                            f"**{float(pp):.2f}pp**"
                        )
                    except (TypeError, ValueError):
                        pass

                second_line = " • ".join(score_details)

                extra_details = [
                    (
                        f"{BeatmapEmbed.format_number(total_score)} "
                        f"score"
                    )
                ]

                if combo is not None:
                    extra_details.append(
                        (
                            f"{BeatmapEmbed.format_number(combo)}x "
                            f"combo"
                        )
                    )

                third_line = " • ".join(extra_details)

                leaderboard_entries.append(
                    f"{first_line}\n"
                    f"{second_line}\n"
                    f"{third_line}"
                )

            embed.add_field(
                name="━━━━━━━━━━━━━━━━━ osu!Romania Top 3 ━━━━━━━━━━━━━━━━━",
                value="\n\n".join(leaderboard_entries),
                inline=False
            )

        else:
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━ osu!Romania Top 3 ━━━━━━━━━━━━━━━━━",
                value=(
                    "No linked player has a score "
                    "on this beatmap yet."
                ),
                inline=False
            )

        footer_parts = [
            f"Mapped by {creator}"
        ]

        if beatmap_id:
            footer_parts.append(
                f"Beatmap #{beatmap_id}"
            )

        if beatmapset_id:
            footer_parts.append(
                f"Set #{beatmapset_id}"
            )

        embed.set_footer(
            text=" • ".join(footer_parts)
        )

        return embed