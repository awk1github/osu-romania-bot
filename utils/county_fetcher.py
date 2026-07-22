import asyncio
import sqlite3
from datetime import datetime, timezone

import aiohttp

from utils.counties import ROMANIAN_COUNTIES

DATABASE_PATH = "database/bot.db"
BASE_URL = "https://osuworld.octo.moe/api"


class CountyFetcher:
    @classmethod
    async def fetch_page(cls, county_code: str, page: int, mode: str = "osu") -> dict:
        url = f"{BASE_URL}/RO/RO-{county_code}/top/{mode}?page={page}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()

    @classmethod
    async def sync_county(cls, county_code: str, mode: str = "osu") -> int:
        county_code = county_code.upper()
        if county_code not in ROMANIAN_COUNTIES:
            raise ValueError(f"Unknown county code: {county_code}")

        county_name = ROMANIAN_COUNTIES[county_code]
        first_page = await cls.fetch_page(county_code, 1, mode)
        total_pages = first_page.get("pages", 1)
        all_players = list(first_page.get("top", []))

        for page in range(2, total_pages + 1):
            data = await cls.fetch_page(county_code, page, mode)
            all_players.extend(data.get("top", []))

        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM osu_counties WHERE county_code = ?", (county_code,))

            for position, player in enumerate(all_players, start=1):
                cursor.execute(
                    '''
                    INSERT INTO osu_counties (
                        osu_id, osu_username, county_code, county_name,
                        county_rank, pp, global_rank, avatar_url, last_updated
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(osu_id) DO UPDATE SET
                        osu_username=excluded.osu_username,
                        county_code=excluded.county_code,
                        county_name=excluded.county_name,
                        county_rank=excluded.county_rank,
                        pp=excluded.pp,
                        global_rank=excluded.global_rank,
                        avatar_url=excluded.avatar_url,
                        last_updated=excluded.last_updated
                    ''',
                    (
                        player["id"],
                        player["username"],
                        county_code,
                        county_name,
                        position,
                        player.get("pp"),
                        player.get("rank"),
                        player.get("avatar_url"),
                        now,
                    ),
                )
            connection.commit()
        return len(all_players)

    @classmethod
    async def sync_all_counties(cls, mode: str = "osu") -> int:
        total_players = 0
        for county_code, county_name in ROMANIAN_COUNTIES.items():
            try:
                print(f"[COUNTIES] Syncing {county_name} ({county_code})...")
                saved = await cls.sync_county(county_code=county_code, mode=mode)
                total_players += saved
                print(f"[COUNTIES] Saved {saved} players for {county_name}.")
            except Exception as error:
                print(f"[COUNTIES] Failed {county_name} ({county_code}): {type(error).__name__}: {error}")
            await asyncio.sleep(1)
        return total_players