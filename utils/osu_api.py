from __future__ import annotations

import logging
import os
import time
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)

ACCESS_TOKEN: str | None = None
TOKEN_EXPIRES: float = 0


class OsuAPI:
    """Small osu! API v2 wrapper used by the bot.

    This version intentionally preserves the bot's previous score behaviour.
    In particular, it does not opt into the 20220705 score response yet and
    does not force ``legacy_only=0``. That prevents existing achievement
    snapshots from being compared against a different family of score IDs.
    """

    BASE_URL = "https://osu.ppy.sh/api/v2"
    TOKEN_URL = "https://osu.ppy.sh/oauth/token"
    REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)

    @staticmethod
    async def get_access_token(force_refresh: bool = False) -> str | None:
        global ACCESS_TOKEN, TOKEN_EXPIRES

        if (
            not force_refresh
            and ACCESS_TOKEN
            and time.time() < TOKEN_EXPIRES
        ):
            return ACCESS_TOKEN

        client_id = os.getenv("OSU_CLIENT_ID")
        client_secret = os.getenv("OSU_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.error("OSU_CLIENT_ID or OSU_CLIENT_SECRET is missing.")
            return None

        try:
            numeric_client_id = int(client_id)
        except ValueError:
            logger.error("OSU_CLIENT_ID must be a number.")
            return None

        payload = {
            "client_id": numeric_client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "public",
        }

        try:
            async with aiohttp.ClientSession(
                timeout=OsuAPI.REQUEST_TIMEOUT
            ) as session:
                async with session.post(
                    OsuAPI.TOKEN_URL,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        body = await response.text()
                        logger.error(
                            "osu! token request failed (%s): %s",
                            response.status,
                            body[:500],
                        )
                        return None

                    data = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            logger.error("osu! token request failed: %s", exc)
            return None

        token = data.get("access_token")
        expires_in = data.get("expires_in")

        if not token or not isinstance(expires_in, (int, float)):
            logger.error("osu! token response was missing required fields.")
            return None

        ACCESS_TOKEN = token
        TOKEN_EXPIRES = time.time() + float(expires_in) - 60
        return ACCESS_TOKEN

    @staticmethod
    async def api_get(
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        """Send an authenticated GET request to the osu! API.

        A 401 response refreshes the OAuth token once. Other unsuccessful
        responses return ``None`` and are logged rather than raising inside a
        Discord command.
        """

        token = await OsuAPI.get_access_token()
        if token is None:
            return None

        url = f"{OsuAPI.BASE_URL}/{endpoint.lstrip('/')}"

        for attempt in range(2):
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }

            try:
                async with aiohttp.ClientSession(
                    timeout=OsuAPI.REQUEST_TIMEOUT
                ) as session:
                    async with session.get(
                        url,
                        headers=headers,
                        params=params,
                    ) as response:
                        if response.status == 401 and attempt == 0:
                            token = await OsuAPI.get_access_token(
                                force_refresh=True
                            )
                            if token is None:
                                return None
                            continue

                        if response.status != 200:
                            body = await response.text()
                            logger.warning(
                                "osu! API GET %s failed (%s): %s",
                                endpoint,
                                response.status,
                                body[:500],
                            )
                            return None

                        return await response.json()
            except (aiohttp.ClientError, TimeoutError) as exc:
                logger.warning("osu! API GET %s failed: %s", endpoint, exc)
                return None

        return None

    # ------------------------
    # USERS
    # ------------------------

    @staticmethod
    async def get_user(
        user: str | int,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        return await OsuAPI.api_get(f"users/{user}/{mode}")

    @staticmethod
    async def get_user_by_id(
        user_id: int,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        """Compatibility alias for older commands."""
        return await OsuAPI.get_user(user_id, mode)

    # ------------------------
    # SCORES
    # ------------------------

    @staticmethod
    async def get_recent(
        user_id: int | str,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        data = await OsuAPI.api_get(
            f"users/{user_id}/scores/recent",
            params={"limit": 1, "mode": mode},
        )

        if not isinstance(data, list) or not data:
            return None

        return data[0]

    @staticmethod
    async def get_score(
        score_id: int | str,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        return await OsuAPI.api_get(f"scores/{mode}/{score_id}")

    @staticmethod
    async def get_top(
        user_id: int | str,
        limit: int = 100,
        mode: str = "osu",
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        data = await OsuAPI.api_get(
            f"users/{user_id}/scores/best",
            params={
                "limit": limit,
                "offset": offset,
                "mode": mode,
            },
        )
        return data if isinstance(data, list) else None

    @staticmethod
    async def get_best(
        user_id: int | str,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        scores = await OsuAPI.get_top(
            user_id,
            limit=1,
            mode=mode,
        )
        return scores[0] if scores else None

    @staticmethod
    async def get_firsts(
        user_id: int | str,
        limit: int = 100,
        mode: str = "osu",
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        data = await OsuAPI.api_get(
            f"users/{user_id}/scores/firsts",
            params={
                "limit": limit,
                "offset": offset,
                "mode": mode,
            },
        )
        return data if isinstance(data, list) else None

    @staticmethod
    async def get_pinned(
        user_id: int | str,
        limit: int = 100,
        mode: str = "osu",
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        data = await OsuAPI.api_get(
            f"users/{user_id}/scores/pinned",
            params={
                "limit": limit,
                "offset": offset,
                "mode": mode,
            },
        )
        return data if isinstance(data, list) else None

    # ------------------------
    # BEATMAPS
    # ------------------------

    @staticmethod
    async def get_beatmap(
        beatmap_id: int | str,
    ) -> dict[str, Any] | None:
        return await OsuAPI.api_get(f"beatmaps/{beatmap_id}")

    @staticmethod
    async def get_beatmapset(
        beatmapset_id: int | str,
    ) -> dict[str, Any] | None:
        return await OsuAPI.api_get(f"beatmapsets/{beatmapset_id}")

    # ------------------------
    # BEATMAP SCORES
    # ------------------------

    @staticmethod
    async def get_user_beatmap_score(
        beatmap_id: int | str,
        user_id: int | str,
        mode: str = "osu",
    ) -> dict[str, Any] | None:
        return await OsuAPI.api_get(
            f"beatmaps/{beatmap_id}/scores/users/{user_id}",
            params={"mode": mode},
        )