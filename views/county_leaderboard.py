import math
import sqlite3
from pathlib import Path

import discord

from views.pagination import PaginationView


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "bot.db"
)

PLAYERS_PER_PAGE = 10


class CountyLeaderboardView(PaginationView):
    def __init__(
        self,
        author_id: int,
        county_code: str,
        county_name: str,
        current_page: int = 1,
    ) -> None:
        self.county_code = county_code
        self.county_name = county_name

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
                FROM osu_counties
                WHERE county_code = ?
                """,
                (self.county_code,),
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
                    osu_id,
                    osu_username,
                    county_rank,
                    pp,
                    global_rank,
                    last_updated
                FROM osu_counties
                WHERE county_code = ?
                ORDER BY county_rank ASC
                LIMIT ? OFFSET ?
                """,
                (
                    self.county_code,
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

        for player in players:
            county_rank = player["county_rank"]
            username = player["osu_username"]
            osu_id = player["osu_id"]
            pp = player["pp"]
            global_rank = player["global_rank"]

            profile_link = (
                f"https://osu.ppy.sh/users/{osu_id}"
            )

            if county_rank is None:
                county_rank_text = "?"
            else:
                county_rank_text = (
                    f"{county_rank:,}"
                )

            if pp is None:
                pp_text = "Unknown PP"
            else:
                pp_text = f"{pp:,.2f}pp"

            if global_rank is None:
                global_rank_text = "Unranked"
            else:
                global_rank_text = (
                    f"Global #{global_rank:,}"
                )

            lines.append(
                (
                    f"**#{county_rank_text}** "
                    f"[{username}]({profile_link})\n"
                    f"{pp_text} • {global_rank_text}"
                )
            )

        embed = discord.Embed(
            title=(
                "📍 Top Players Leaderboards from "
                f"{self.county_name}"
            ),
            description=(
                "**Leaderboard based on "
                "performance points!**\n\n"
                + "\n\n".join(lines)
            ),
            color=discord.Color.blurple(),
        )

        embed.set_footer(
            text=(
                f"Page {page}/{self.total_pages} • "
                f"{self.total_players} players"
            )
        )

        return embed