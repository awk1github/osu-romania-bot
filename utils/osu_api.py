import os
import time
import aiohttp


ACCESS_TOKEN = None
TOKEN_EXPIRES = 0


class OsuAPI:

    BASE_URL = "https://osu.ppy.sh/api/v2"

    @staticmethod
    async def get_access_token():
        global ACCESS_TOKEN, TOKEN_EXPIRES

        # Reuse token until shortly before it expires
        if ACCESS_TOKEN and time.time() < TOKEN_EXPIRES:
            return ACCESS_TOKEN

        url = "https://osu.ppy.sh/oauth/token"

        payload = {
            "client_id": int(os.getenv("OSU_CLIENT_ID")),
            "client_secret": os.getenv("OSU_CLIENT_SECRET"),
            "grant_type": "client_credentials",
            "scope": "public"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:

                if response.status != 200:
                    return None

                data = await response.json()

        ACCESS_TOKEN = data["access_token"]
        TOKEN_EXPIRES = time.time() + data["expires_in"] - 60

        return ACCESS_TOKEN

    @staticmethod
    async def api_get(endpoint: str):
        """
        Sends an authenticated GET request to the osu! API.
        """

        token = await OsuAPI.get_access_token()

        if token is None:
            return None

        headers = {
            "Authorization": f"Bearer {token}"
        }

        url = f"{OsuAPI.BASE_URL}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:

                if response.status != 200:
                    return None

                return await response.json()

    # ------------------------
    # USERS
    # ------------------------

    @staticmethod
    async def get_user(username: str):
        return await OsuAPI.api_get(
            f"users/{username}/osu"
        )

    @staticmethod
    async def get_user_by_id(user_id: int):
        return await OsuAPI.api_get(
            f"users/{user_id}/osu"
        )

    # ------------------------
    # SCORES
    # ------------------------

    @staticmethod
    async def get_recent(user_id: int):
        data = await OsuAPI.api_get(
            f"users/{user_id}/scores/recent?limit=1"
        )

        if not data:
            return None

        return data[0]

    @staticmethod
    async def get_score(score_id: int):
        return await OsuAPI.api_get(
            f"scores/{score_id}"
        )
    
    @staticmethod
    async def get_top(user_id: int):
        return await OsuAPI.api_get(
            f"users/{user_id}/scores/best"
        )

    @staticmethod
    async def get_best(user_id: int):
        data = await OsuAPI.api_get(
            f"users/{user_id}/scores/best?limit=1"
        )

        if not data:
            return None

        return data[0]

    @staticmethod
    async def get_firsts(user_id: int):
        return await OsuAPI.api_get(
            f"users/{user_id}/scores/firsts"
        )

    @staticmethod
    async def get_pinned(user_id: int):
        return await OsuAPI.api_get(
            f"users/{user_id}/scores/pinned"
        )
    
    # ------------------------
    # BEATMAPS
    # ------------------------

    @staticmethod
    async def get_beatmap(beatmap_id: int | str):
        return await OsuAPI.api_get(
            f"beatmaps/{beatmap_id}"
    )

    # ------------------------
    # BEATMAP SCORES
    # ------------------------

    @staticmethod
    async def get_user_beatmap_score(
        beatmap_id: int | str,
        user_id: int | str
    ) -> dict | None:
        """
        Returns a user's best score on a specific beatmap.
        """

        return await OsuAPI.api_get(
            f"beatmaps/{beatmap_id}/scores/users/{user_id}"
        )