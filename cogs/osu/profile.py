import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from utils.cache import refresh_player
from utils.embeds import EmbedFactory
from utils.osu_api import OsuAPI
from utils.osu_embed import OsuEmbed
from views.profile import ProfileView
from utils.osu_oauth import OsuOAuth


DATABASE_PATH = "database/bot.db"


class Profile(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

    # --------------------------------------------------
    # LINK
    # --------------------------------------------------

        @app_commands.command(
            name="link",
            description="Verify and link your osu! account.",
        )
        async def link(
                interaction: discord.Interaction,
            ) -> None:

            if interaction.guild is None:
                await interaction.response.send_message(
                    embed=EmbedFactory.error(
                        "Server Only",
                        "Use this command inside the Discord server.",
                    ),
                    ephemeral=True,
                )
                return

            # Check whether this Discord account is already linked.
            with sqlite3.connect("database/bot.db") as connection:
                existing_account = connection.execute(
                    """
                    SELECT osu_id, osu_username
                    FROM osu_accounts
                    WHERE discord_id = ?
                    """,
                    (interaction.user.id,),
                ).fetchone()

            if existing_account is not None:
                _, osu_username = existing_account

                await interaction.response.send_message(
                    embed=EmbedFactory.info(
                        "Account Already Linked",
                        (
                            "Your Discord account is already linked to "
                            f"**{osu_username}**."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            try:
                authorization_url = (
                    OsuOAuth.create_authorization_url(
                        discord_id=interaction.user.id,
                        guild_id=interaction.guild.id,
                    )
                )
            except Exception as error:
                print(
                    "[OSU OAUTH] Failed to create authorization URL: "
                    f"{type(error).__name__}: {error}"
                )

                await interaction.response.send_message(
                    embed=EmbedFactory.error(
                        "Verification Unavailable",
                        (
                            "The verification link could not be created. "
                            "Please contact a server administrator."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            view = discord.ui.View(timeout=600)

            view.add_item(
                discord.ui.Button(
                    label="Link osu! account",
                    style=discord.ButtonStyle.link,
                    url=authorization_url,
                    emoji="🔗",
                )
            )

            embed = discord.Embed(
                title="Verify your osu! account",
                description=(
                    "Press the button below and authorize the "
                    "osu!Romania application.\n\n"
                    "After verification, you will receive the "
                    "**Member** role and gain access to the server.\n\n"
                    "This link expires in **10 minutes**."
                ),
                color=discord.Color.blurple(),
            )

            embed.set_footer(
                text="Only authorize the official osu!Romania application."
            )

            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True,
            )
    # --------------------------------------------------
    # PROFILE
    # --------------------------------------------------

    @app_commands.command(
        name="profile",
        description="View an osu! profile.",
    )
    @app_commands.describe(
        username=(
            "The osu! username to view. "
            "Leave empty to view your linked account."
        ),
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        username: str | None = None,
    ) -> None:
        await interaction.response.defer()

        if username is None:
            with sqlite3.connect(
                DATABASE_PATH
            ) as connection:
                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT osu_id
                    FROM osu_accounts
                    WHERE discord_id = ?
                    """,
                    (interaction.user.id,),
                )

                row = cursor.fetchone()

            if row is None:
                embed = EmbedFactory.error(
                    "Account Not Linked",
                    (
                        "Use `/link <username>` first "
                        "or specify a username."
                    ),
                )

                await interaction.followup.send(
                    embed=embed
                )
                return

            osu_id = row[0]

        else:
            found_user = await OsuAPI.get_user(
                username
            )

            if found_user is None:
                embed = EmbedFactory.error(
                    "Player Not Found",
                    "That osu! player doesn't exist.",
                )

                await interaction.followup.send(
                    embed=embed
                )
                return

            osu_id = found_user["id"]

        try:
            await refresh_player(osu_id)
        except Exception as error:
            print(
                "[PROFILE] Player cache refresh failed: "
                f"{type(error).__name__}: {error}"
            )

        user = await OsuAPI.get_user(osu_id)

        if user is None:
            embed = EmbedFactory.error(
                "Player Not Found",
                (
                    "Couldn't retrieve that "
                    "osu! profile."
                ),
            )

            await interaction.followup.send(
                embed=embed
            )
            return

        embed = OsuEmbed.profile(user)

        view = ProfileView(
            author_id=interaction.user.id,
            user=user,
        )

        await interaction.followup.send(
            embed=embed,
            view=view,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        Profile(bot)
    )