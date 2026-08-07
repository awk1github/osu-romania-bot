from __future__ import annotations

import asyncio
import logging
import os
import time
import json

from typing import Any
from urllib.parse import quote
from collections import OrderedDict

import aiohttp
import rosu_pp_py


logger = logging.getLogger(__name__)

ACCESS_TOKEN: str | None = None
TOKEN_EXPIRES = 0.0
TOKEN_LOCK = asyncio.Lock()

BEATMAP_CACHE: OrderedDict[int, bytes] = OrderedDict()
BEATMAP_CACHE_LIMIT = 128

class OsuAPI:
    """Small asynchronous wrapper around the public osu! API v2."""

    BASE_URL = "https://osu.ppy.sh/api/v2"
    TOKEN_URL = "https://osu.ppy.sh/oauth/token"
    API_VERSION = "20220705"
    REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)

    SESSION: aiohttp.ClientSession | None = None
    SESSION_LOCK = asyncio.Lock()

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls.SESSION is not None and not cls.SESSION.closed:
            return cls.SESSION

        async with cls.SESSION_LOCK:
            if cls.SESSION is None or cls.SESSION.closed:
                connector = aiohttp.TCPConnector(
                    limit=100,
                    limit_per_host=5,
                    ttl_dns_cache=300,
                )

                cls.SESSION = aiohttp.ClientSession(
                    timeout=cls.REQUEST_TIMEOUT,
                    connector=connector,
                )

        return cls.SESSION

    @classmethod
    async def close_session(cls) -> None:
        if cls.SESSION is not None and not cls.SESSION.closed:
            await cls.SESSION.close()

        cls.SESSION = None

    @staticmethod
    async def get_access_token(force_refresh: bool = False) -> str | None:
        global ACCESS_TOKEN, TOKEN_EXPIRES

        if (
            not force_refresh
            and ACCESS_TOKEN
            and time.time() < TOKEN_EXPIRES
        ):
            return ACCESS_TOKEN

        async with TOKEN_LOCK:
            if (
                not force_refresh
                and ACCESS_TOKEN
                and time.time() < TOKEN_EXPIRES
            ):
                return ACCESS_TOKEN

            client_id = os.getenv("OSU_CLIENT_ID")
            client_secret = os.getenv("OSU_CLIENT_SECRET")

            if not client_id or not client_secret:
                logger.error(
                    "OSU_CLIENT_ID or OSU_CLIENT_SECRET is not configured."
                )
                return None

            payload = {
                "client_id": int(client_id),
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": "public",
            }

            try:
                session = await OsuAPI.get_session()

                async with session.post(
                    OsuAPI.TOKEN_URL,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        body = await response.text()
                        logger.error(
                            "osu! OAuth failed with HTTP %s: %s",
                            response.status,
                            body[:500],
                        )
                        return None

                    data = await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError):
                logger.exception("Failed to request an osu! OAuth token.")
                return None

            token = data.get("access_token")
            expires_in = data.get("expires_in")

            if not token or expires_in is None:
                logger.error("osu! OAuth returned an invalid token response.")
                return None

            ACCESS_TOKEN = str(token)
            TOKEN_EXPIRES = time.time() + float(expires_in) - 60

            return ACCESS_TOKEN

    @staticmethod
    async def api_get(
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        """Send an authenticated GET request to osu! API v2."""

        endpoint = endpoint.lstrip("/")
        url = f"{OsuAPI.BASE_URL}/{endpoint}"

        for attempt in range(2):
            token = await OsuAPI.get_access_token(
                force_refresh=attempt == 1
            )

            if token is None:
                return None

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "x-api-version": OsuAPI.API_VERSION,
            }

            try:
                session = await OsuAPI.get_session()

                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                ) as response:
                        if response.status == 401 and attempt == 0:
                            continue

                        if response.status == 404:
                            return None

                        if response.status == 429:
                            retry_after = response.headers.get("Retry-After", "1")
                            try:
                                delay = min(float(retry_after), 10.0)
                            except ValueError:
                                delay = 1.0

                            logger.warning(
                                "osu! API rate limited %s; retrying in %.1fs.",
                                endpoint,
                                delay,
                            )
                            await asyncio.sleep(delay)
                            continue

                        if response.status != 200:
                            body = await response.text()
                            logger.error(
                                "osu! API GET %s failed with HTTP %s: %s",
                                endpoint,
                                response.status,
                                body[:500],
                            )
                            return None

                        return await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError):
                logger.exception("osu! API request failed: GET %s", endpoint)
                return None

        return None

    # USERS

    @staticmethod
    async def get_user(
        user: str | int,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        user_value = quote(str(user), safe="")
        data = await OsuAPI.api_get(
            f"users/{user_value}/{mode}",
            params={"key": "id" if isinstance(user, int) else "username"},
        )
        return data if isinstance(data, dict) else None

    # USER SCORES

    @staticmethod
    async def get_user_scores(
        user_id: int,
        score_type: str,
        *,
        mode: str = "osu",
        limit: int = 50,
        offset: int = 0,
        include_fails: bool = False,
        legacy_only: bool = False,
    ) -> list[dict[str, Any]]:
        if score_type not in {"best", "recent", "firsts", "pinned"}:
            raise ValueError(f"Unsupported score type: {score_type}")

        params: dict[str, Any] = {
            "mode": mode,
            "limit": max(1, min(int(limit), 100)),
            "offset": max(0, int(offset)),
            "legacy_only": int(legacy_only),
        }

        if score_type == "recent":
            params["include_fails"] = int(include_fails)

        data = await OsuAPI.api_get(
            f"users/{int(user_id)}/scores/{score_type}",
            params=params,
        )

        return data if isinstance(data, list) else []

    @staticmethod
    async def get_recent(
        user_id: int,
        *,
        mode: str = "osu",
        include_fails: bool = False,
    ) -> dict[str, Any] | None:
        scores = await OsuAPI.get_user_scores(
            user_id,
            "recent",
            mode=mode,
            limit=1,
            include_fails=include_fails,
        )
        return scores[0] if scores else None

    @staticmethod
    async def get_top(
        user_id: int,
        *,
        mode: str = "osu",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await OsuAPI.get_user_scores(
            user_id,
            "best",
            mode=mode,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_best(
        user_id: int,
        *,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        scores = await OsuAPI.get_top(user_id, mode=mode, limit=1)
        return scores[0] if scores else None

    @staticmethod
    async def get_firsts(
        user_id: int,
        *,
        mode: str = "osu",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await OsuAPI.get_user_scores(
            user_id,
            "firsts",
            mode=mode,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_pinned(
        user_id: int,
        *,
        mode: str = "osu",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await OsuAPI.get_user_scores(
            user_id,
            "pinned",
            mode=mode,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_score(
        score_id: int,
        *,
        ruleset: str = "osu",
    ) -> dict[str, Any] | None:
        data = await OsuAPI.api_get(
            f"scores/{ruleset}/{int(score_id)}"
        )

        if data is None:
            # Some score IDs are accepted by the ruleset-less route.
            data = await OsuAPI.api_get(f"scores/{int(score_id)}")

        return data if isinstance(data, dict) else None
    
    @staticmethod
    async def get_legacy_score(
        score_id: int,
        mode: str = "osu",
    ):
        return await OsuAPI.api_get(
            f"scores/{mode}/{score_id}"
        )

    @staticmethod
    async def get_beatmap_file(beatmap_id: int) -> bytes | None:
        if beatmap_id in BEATMAP_CACHE:
            BEATMAP_CACHE.move_to_end(beatmap_id)
            return BEATMAP_CACHE[beatmap_id]

        url = f"https://osu.ppy.sh/osu/{beatmap_id}"

        session = await OsuAPI.get_session()

        async with session.get(url) as response:
            if response.status != 200:
                return None

            data = await response.read()

        BEATMAP_CACHE[beatmap_id] = data

        if len(BEATMAP_CACHE) > BEATMAP_CACHE_LIMIT:
            BEATMAP_CACHE.popitem(last=False)

        return data

    @staticmethod
    async def calculate_pp_values(
        score: dict[str, Any],
    ) -> tuple[float | None, float | None]:
        """
        Calculate:
        1. PP for the actual play.
        2. PP if the play was FC'd at the same accuracy.

        This allows PP to be displayed even when osu!'s API doesn't
        provide PP, such as on unranked/loved maps.
        """
        beatmap = score.get("beatmap") or {}
        beatmap_id = beatmap.get("id") or score.get("beatmap_id")

        if beatmap_id is None:
            return None, None

        beatmap_bytes = await OsuAPI.get_beatmap_file(int(beatmap_id))
        if beatmap_bytes is None:
            return None, None

        mods = score.get("mods") or []

        mod_acronyms: set[str] = set()

        for mod in mods:
            if isinstance(mod, str):
                mod_acronyms.add(mod.upper())

            elif isinstance(mod, dict):
                acronym = mod.get("acronym")

                if acronym:
                    mod_acronyms.add(str(acronym).upper())

        # Classic/stable scores contain CL.
        # Scores without CL use lazer scoring.
        lazer = "CL" not in mod_acronyms

        try:
            accuracy = float(score.get("accuracy") or 0.0) * 100.0
        except (TypeError, ValueError):
            accuracy = 0.0

        accuracy = max(0.0, min(100.0, accuracy))

        statistics = score.get("statistics") or {}

        misses = statistics.get("miss")

        if misses is None:
            misses = statistics.get("count_miss", 0)

        try:
            misses = int(misses or 0)
        except (TypeError, ValueError):
            misses = 0

        combo = score.get("max_combo")

        if combo is None:
            combo = score.get("maximum_combo")

        try:
            combo = int(combo) if combo is not None else None
        except (TypeError, ValueError):
            combo = None

        def calculate() -> tuple[float | None, float | None]:
            parsed_map = rosu_pp_py.Beatmap(bytes=beatmap_bytes)

            if parsed_map.is_suspicious():
                return None, None

            common = {
                "mods": mods,
                "accuracy": accuracy,
                "lazer": lazer,
                "hitresult_priority": (
                    rosu_pp_py.HitResultPriority.BestCase
                ),
            }

            current_args = {
                **common,
                "misses": misses,
            }

            if combo is not None:
                current_args["combo"] = combo

            current_pp = rosu_pp_py.Performance(
                **current_args,
            ).calculate(parsed_map).pp

            # IF FC:
            # Keep the score's accuracy + mods,
            # remove misses,
            # and let rosu use full map combo.
            fc_pp = rosu_pp_py.Performance(
                **common,
                misses=0,
            ).calculate(parsed_map).pp

            return current_pp, fc_pp

        try:
            return await asyncio.to_thread(calculate)

        except Exception:
            logger.exception(
                "PP calculation failed for beatmap %s",
                beatmap_id,
            )

            return None, None

    @staticmethod
    async def calculate_fc_pp(score) -> float | None:
        """
        Compatibility wrapper for existing callers.
        """
        if isinstance(score, str):
            score = json.loads(score)

        _, fc_pp = await OsuAPI.calculate_pp_values(score)

        return fc_pp

    # BEATMAPS

    @staticmethod
    async def get_beatmap(beatmap_id: int) -> dict[str, Any] | None:
        data = await OsuAPI.api_get(f"beatmaps/{int(beatmap_id)}")
        return data if isinstance(data, dict) else None

    @staticmethod
    async def get_beatmapset(beatmapset_id: int) -> dict[str, Any] | None:
        data = await OsuAPI.api_get(
            f"beatmapsets/{int(beatmapset_id)}"
        )
        return data if isinstance(data, dict) else None

    @staticmethod
    async def get_user_beatmap_score(
        beatmap_id: int | str,
        user_id: int | str,
        *,
        ruleset: str = "osu",
        legacy_only: bool = False,
    ) -> dict[str, Any] | None:
        data = await OsuAPI.api_get(
            f"beatmaps/{int(beatmap_id)}/scores/users/{int(user_id)}",
            params={
                "ruleset": ruleset,
                "legacy_only": int(legacy_only),
            },
        )
        return data if isinstance(data, dict) else None

    @staticmethod
    async def enrich_score(
        score: dict[str, Any],
        *,
        include_user: bool = True,
        include_beatmap: bool = True,
        include_beatmapset: bool = True,
    ) -> dict[str, Any]:
        """Fill compact score relations with complete API objects."""

        enriched = dict(score)
        compact_beatmap = score.get("beatmap") or {}

        user_id = score.get("user_id") or (score.get("user") or {}).get("id")
        beatmap_id = score.get("beatmap_id") or compact_beatmap.get("id")
        beatmapset_id = compact_beatmap.get("beatmapset_id")

        if beatmapset_id is None:
            beatmapset_id = (score.get("beatmapset") or {}).get("id")

        jobs: list[tuple[str, Any]] = []

        if include_user and user_id is not None:
            jobs.append(("user", OsuAPI.get_user(int(user_id))))

        if include_beatmap and beatmap_id is not None:
            jobs.append(("beatmap", OsuAPI.get_beatmap(int(beatmap_id))))

        if include_beatmapset and beatmapset_id is not None:
            jobs.append(
                ("beatmapset", OsuAPI.get_beatmapset(int(beatmapset_id)))
            )

        if jobs:
            results = await asyncio.gather(
                *(job for _, job in jobs),
                return_exceptions=True,
            )

            for (key, _), result in zip(jobs, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "Failed to enrich score relation %s: %r",
                        key,
                        result,
                    )
                    continue

                if result:
                    enriched[key] = result

        return enriched
