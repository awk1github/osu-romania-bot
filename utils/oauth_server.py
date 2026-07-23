import html
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web
import discord
from discord.ext import commands
from utils.rank_roles import RankRoleService


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "bot.db"
)

OSU_TOKEN_URL = "https://osu.ppy.sh/oauth/token"
OSU_ME_URL = "https://osu.ppy.sh/api/v2/me/osu"

OSU_CLIENT_ID = os.getenv("OSU_CLIENT_ID")
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
OSU_REDIRECT_URI = os.getenv("OSU_REDIRECT_URI")

OAUTH_HOST = os.getenv("OAUTH_HOST", "0.0.0.0")
OAUTH_PORT = int(os.getenv("OAUTH_PORT", "8080"))

MEMBER_ROLE_ID = int(os.getenv("MEMBER_ROLE_ID", "0") or 0)


class OAuthServer:
    """Small aiohttp server used for the osu! OAuth callback."""

    runner: web.AppRunner | None = None
    site: web.TCPSite | None = None
    bot: commands.Bot | None = None

    @classmethod
    async def start(cls, bot: commands.Bot) -> None:
        if cls.runner is not None:
            return

        cls._validate_configuration()
        cls.bot = bot

        app = web.Application()

        app.router.add_get("/", cls.health_check)
        app.router.add_get("/osu/callback", cls.osu_callback)

        cls.runner = web.AppRunner(app)
        await cls.runner.setup()

        cls.site = web.TCPSite(
            cls.runner,
            host=OAUTH_HOST,
            port=OAUTH_PORT,
        )
        await cls.site.start()

        print(
            f"[OSU OAUTH] Callback server listening on "
            f"{OAUTH_HOST}:{OAUTH_PORT}"
        )

    @classmethod
    async def stop(cls) -> None:
        if cls.runner is not None:
            await cls.runner.cleanup()

        cls.runner = None
        cls.site = None
        cls.bot = None

    @staticmethod
    def _validate_configuration() -> None:
        missing: list[str] = []

        if not OSU_CLIENT_ID:
            missing.append("OSU_CLIENT_ID")
        if not OSU_CLIENT_SECRET:
            missing.append("OSU_CLIENT_SECRET")
        if not OSU_REDIRECT_URI:
            missing.append("OSU_REDIRECT_URI")
        if MEMBER_ROLE_ID <= 0:
            missing.append("MEMBER_ROLE_ID")

        if missing:
            raise RuntimeError(
                "Missing or invalid OAuth environment variables: "
                + ", ".join(missing)
            )

    @staticmethod
    async def health_check(request: web.Request) -> web.Response:
        del request
        return web.Response(
            text="osu!Romania OAuth server is running.",
            content_type="text/plain",
        )

    @classmethod
    async def osu_callback(
        cls,
        request: web.Request,
    ) -> web.Response:
        oauth_error = request.query.get("error")
        if oauth_error:
            return cls._html_response(
                title="Authorization cancelled",
                message=(
                    "The osu! authorization was cancelled or denied. "
                    "You can return to Discord and run /link again."
                ),
                success=False,
                status=400,
            )

        code = request.query.get("code")
        state = request.query.get("state")

        if not code or not state:
            return cls._html_response(
                title="Invalid callback",
                message="The callback is missing its code or state.",
                success=False,
                status=400,
            )

        state_row = cls._consume_state(state)

        if state_row is None:
            return cls._html_response(
                title="Invalid or expired link",
                message=(
                    "This verification link has expired or was already used. "
                    "Return to Discord and run /link again."
                ),
                success=False,
                status=400,
            )

        discord_id, guild_id = state_row

        try:
            access_token = await cls._exchange_code(code)
            osu_user = await cls._fetch_authenticated_user(access_token)
        except OAuthRequestError as error:
            print(f"[OSU OAUTH] API failure: {error}")
            return cls._html_response(
                title="osu! verification failed",
                message=(
                    "The bot could not verify your osu! account. "
                    "Return to Discord and run /link again."
                ),
                success=False,
                status=502,
            )
        except Exception as error:
            print(
                "[OSU OAUTH] Unexpected callback error: "
                f"{type(error).__name__}: {error}"
            )
            return cls._html_response(
                title="Verification error",
                message="An unexpected error occurred during verification.",
                success=False,
                status=500,
            )

        osu_id = cls._to_int(osu_user.get("id"))
        osu_username = str(osu_user.get("username") or "Unknown")

        if osu_id is None:
            return cls._html_response(
                title="Invalid osu! response",
                message="osu! did not return a valid account ID.",
                success=False,
                status=502,
            )

        linked_discord_id = cls._get_discord_id_for_osu_account(osu_id)

        if (
            linked_discord_id is not None
            and linked_discord_id != discord_id
        ):
            return cls._html_response(
                title="Account already linked",
                message=(
                    f"The osu! account {osu_username} is already linked "
                    "to another Discord account."
                ),
                success=False,
                status=409,
            )

        try:
            cls._save_account(
                discord_id=discord_id,
                osu_user=osu_user,
            )
        except sqlite3.Error as error:
            print(f"[OSU OAUTH] Database failure: {error}")
            return cls._html_response(
                title="Database error",
                message=(
                    "Your osu! account was verified, but the bot could not "
                    "save the link. Please contact an administrator."
                ),
                success=False,
                status=500,
            )

        role_result = await cls._grant_member_role(
            guild_id=guild_id,
            discord_id=discord_id,
        )

        statistics = osu_user.get("statistics") or {}
        global_rank = cls._to_int(statistics.get("global_rank"))

        rank_role_result = await cls._grant_rank_role(
            guild_id=guild_id,
            discord_id=discord_id,
            global_rank=global_rank,
        )

        if role_result is None:
            role_message = (
                "Your account was linked, but the Member role could not be "
                "assigned automatically. Please contact an administrator."
            )
        elif rank_role_result is None:
            role_message = (
                "Your Member role was assigned, but your osu! rank role "
                "could not be updated automatically. You can now return "
                "to Discord."
            )
        else:
            role_message = (
                "Your Member role and osu! rank role have been updated. "
                "You can now return to Discord."
            )

        return cls._html_response(
            title="Verification successful",
            message=(
                f"Your Discord account is now linked to "
                f"{osu_username}. {role_message}"
            ),
            success=True,
            status=200,
        )

    @staticmethod
    def _consume_state(state: str) -> tuple[int, int] | None:
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(DATABASE_PATH) as connection:
            row = connection.execute(
                """
                SELECT discord_id, guild_id, expires_at
                FROM osu_oauth_states
                WHERE state = ?
                """,
                (state,),
            ).fetchone()

            if row is None:
                return None

            discord_id, guild_id, expires_at = row

            connection.execute(
                """
                DELETE FROM osu_oauth_states
                WHERE state = ?
                """,
                (state,),
            )

            connection.execute(
                """
                DELETE FROM osu_oauth_states
                WHERE expires_at <= ?
                """,
                (now,),
            )

        try:
            expiry = datetime.fromisoformat(expires_at)

            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            if expiry <= datetime.now(timezone.utc):
                return None
        except (TypeError, ValueError):
            return None

        return int(discord_id), int(guild_id)

    @staticmethod
    async def _exchange_code(code: str) -> str:
        payload = {
            "client_id": int(OSU_CLIENT_ID),
            "client_secret": OSU_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": OSU_REDIRECT_URI,
        }

        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                OSU_TOKEN_URL,
                json=payload,
                headers={"Accept": "application/json"},
            ) as response:
                data = await OAuthServer._read_json(response)

                if response.status != 200:
                    raise OAuthRequestError(
                        f"Token exchange returned HTTP {response.status}: "
                        f"{data}"
                    )

        access_token = data.get("access_token")

        if not access_token:
            raise OAuthRequestError(
                "Token response did not contain an access token."
            )

        return str(access_token)

    @staticmethod
    async def _fetch_authenticated_user(
        access_token: str,
    ) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=15)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                OSU_ME_URL,
                headers=headers,
            ) as response:
                data = await OAuthServer._read_json(response)

                if response.status != 200:
                    raise OAuthRequestError(
                        f"User lookup returned HTTP {response.status}: "
                        f"{data}"
                    )

        if not isinstance(data, dict):
            raise OAuthRequestError(
                "Authenticated user response was not an object."
            )

        return data

    @staticmethod
    async def _read_json(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        try:
            data = await response.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError):
            text = await response.text()
            return {"raw_response": text[:500]}

        return data if isinstance(data, dict) else {"data": data}

    @staticmethod
    def _get_discord_id_for_osu_account(
        osu_id: int,
    ) -> int | None:
        with sqlite3.connect(DATABASE_PATH) as connection:
            row = connection.execute(
                """
                SELECT discord_id
                FROM osu_accounts
                WHERE osu_id = ?
                """,
                (osu_id,),
            ).fetchone()

        return int(row[0]) if row is not None else None

    @staticmethod
    def _save_account(
        discord_id: int,
        osu_user: dict[str, Any],
    ) -> None:
        statistics = osu_user.get("statistics") or {}

        osu_id = OAuthServer._to_int(osu_user.get("id"))
        if osu_id is None:
            raise ValueError("Missing osu! user ID.")

        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(
                """
                INSERT INTO osu_accounts (
                    discord_id,
                    osu_id,
                    osu_username,
                    pp,
                    global_rank,
                    country_rank,
                    accuracy,
                    avatar_url,
                    country_code,
                    last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(discord_id) DO UPDATE SET
                    osu_id = excluded.osu_id,
                    osu_username = excluded.osu_username,
                    pp = excluded.pp,
                    global_rank = excluded.global_rank,
                    country_rank = excluded.country_rank,
                    accuracy = excluded.accuracy,
                    avatar_url = excluded.avatar_url,
                    country_code = excluded.country_code,
                    last_updated = datetime('now')
                """,
                (
                    discord_id,
                    osu_id,
                    osu_user.get("username"),
                    statistics.get("pp"),
                    statistics.get("global_rank"),
                    statistics.get("country_rank"),
                    statistics.get("hit_accuracy"),
                    osu_user.get("avatar_url"),
                    osu_user.get("country_code"),
                ),
            )

    @classmethod
    async def _grant_member_role(
        cls,
        guild_id: int,
        discord_id: int,
    ) -> bool | None:
        if cls.bot is None:
            return None

        guild = cls.bot.get_guild(guild_id)
        if guild is None:
            return None

        role = guild.get_role(MEMBER_ROLE_ID)
        if role is None:
            return None

        member = guild.get_member(discord_id)

        if member is None:
            try:
                member = await guild.fetch_member(discord_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None

        if role in member.roles:
            return True

        bot_member = guild.me

        if (
            bot_member is None
            or role.managed
            or role >= bot_member.top_role
        ):
            return None

        try:
            await member.add_roles(
                role,
                reason="Verified osu! account through OAuth",
            )
        except (discord.Forbidden, discord.HTTPException):
            return None

        return True

    @classmethod
    async def _grant_rank_role(
        cls,
        guild_id: int,
        discord_id: int,
        global_rank: int | None,
    ) -> bool | None:
        if cls.bot is None or global_rank is None:
            return None

        guild = cls.bot.get_guild(guild_id)

        if guild is None:
            return None

        member = guild.get_member(discord_id)

        if member is None:
            try:
                member = await guild.fetch_member(discord_id)
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
            ):
                return None

        try:
            return await RankRoleService.update_member(
                member,
                global_rank,
            )
        except Exception as error:
            print(
                "[OSU OAUTH] Rank role assignment failed: "
                f"{type(error).__name__}: {error}"
            )
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _html_response(
        title: str,
        message: str,
        success: bool,
        status: int,
    ) -> web.Response:
        safe_title = html.escape(title)
        safe_message = html.escape(message)

        accent = "#57f287" if success else "#ed4245"
        icon = "✓" if success else "×"

        page = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 24px;
            background: #0f1015;
            color: #f2f3f5;
            font-family: Arial, sans-serif;
        }}
        .card {{
            width: min(520px, 100%);
            padding: 36px;
            border: 1px solid #2b2d31;
            border-radius: 18px;
            background: #1e1f22;
            text-align: center;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
        }}
        .icon {{
            width: 72px;
            height: 72px;
            margin: 0 auto 20px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: {accent};
            color: #111214;
            font-size: 42px;
            font-weight: 700;
        }}
        h1 {{ margin: 0 0 14px; font-size: 28px; }}
        p {{ margin: 0; color: #b5bac1; line-height: 1.6; }}
    </style>
</head>
<body>
    <main class="card">
        <div class="icon">{icon}</div>
        <h1>{safe_title}</h1>
        <p>{safe_message}</p>
    </main>
</body>
</html>
"""

        return web.Response(
            text=page,
            status=status,
            content_type="text/html",
        )


class OAuthRequestError(RuntimeError):
    pass