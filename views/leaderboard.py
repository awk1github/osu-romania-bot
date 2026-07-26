import math
import sqlite3
from pathlib import Path

import discord

from views.pagination import PaginationView


DATABASE_PATH = Path("database/bot.db")

PLAYERS_PER_PAGE = 10

def country_code_to_flag(
    country_code: str | None,
) -> str:
    if not country_code or len(country_code) != 2:
        return "🌐"

    return "".join(
        chr(ord(character) + 127397)
        for character in country_code.upper()
    )


class ServerLeaderboardView(PaginationView):
    def __init__(
        self,
        author_id: int,
        current_page: int = 1,
    ) -> None:
        self.author_id = author_id
        self.total_players = self.get_total_players()

        self.total_pages = max(
            1,
            math.ceil(
                self.total_players / PLAYERS_PER_PAGE
            ),
        )

        super().__init__(
            author_id=author_id,
            current_page=current_page,
            max_pages=self.total_pages,
            callback=self.build_page,
        )

    def get_total_players(self) -> int:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM osu_accounts
                WHERE pp IS NOT NULL
                """
            )

            result = cursor.fetchone()

            if result is None:
                return 0

            return result[0]

    def get_players(
        self,
        page: int,
    ) -> list[sqlite3.Row]:
        offset = (
            page - 1
        ) * PLAYERS_PER_PAGE

        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    discord_id,
                    osu_id,
                    osu_username,
                    pp,
                    global_rank,
                    country_rank,
                    accuracy,
                    country_code
                FROM osu_accounts
                WHERE pp IS NOT NULL
                ORDER BY pp DESC
                LIMIT ? OFFSET ?
                """,
                (
                    PLAYERS_PER_PAGE,
                    offset,
                ),
            )

            return cursor.fetchall()

    async def build_page(
        self,
        page: int,
    ) -> discord.Embed:
        players = self.get_players(page)

        lines: list[str] = []

        country_code = player["country_code"]

        for index, player in enumerate(players):
            server_rank = (
                (page - 1) * PLAYERS_PER_PAGE
                + index
                + 1
            )

            discord_id = player["discord_id"]
            osu_id = player["osu_id"]
            username = player["osu_username"]
            pp = player["pp"]
            global_rank = player["global_rank"]
            country_rank = player["country_rank"]
            accuracy = player["accuracy"]
            country_flag = country_code_to_flag(country_code)

            profile_link = (
                f"https://osu.ppy.sh/users/{osu_id}"
            )

            you = (
                " ⭐"
                if discord_id == self.author_id
                else ""
            )

            if server_rank == 1:
                rank_display = "🥇"
            elif server_rank == 2:
                rank_display = "🥈"
            elif server_rank == 3:
                rank_display = "🥉"
            else:
                rank_display = f"**#{server_rank}**"

            if global_rank is None:
                global_text = "Unranked"
            else:
                global_text = (
                    f"#{global_rank:,}"
                )

            if country_rank is None:
                country_text = "Unranked"
            else:
                country_text = (
                    f"#{country_rank:,}"
                )

            if pp is None:
                pp_text = "Unknown PP"
            else:
                pp_text = f"{pp:,.0f}pp"

            if accuracy is None:
                accuracy_text = "Unknown"
            else:
                accuracy_text = (
                    f"{accuracy:.2f}%"
                )

            lines.append(
                (
                    f"{rank_display} "
                    f"**[{username}]({profile_link})**"
                    f"{you}\n"
                    f"💎 **{pp_text}** • "
                    f"🌍 **{global_text}** • "
                    f"{country_flag} **{country_text}** • "
                    f"🎯 **{accuracy_text}**"
                )
            )

        embed = discord.Embed(
            title="🏆 osu!Romania Leaderboard",
            description="\n\n".join(lines),
            color=discord.Color.gold(),
        )

        embed.set_footer(
            text=(
                f"Page {page}/{self.total_pages} • "
                f"{self.total_players} players • "
                "⭐ = You"
            )
        )

        return embed