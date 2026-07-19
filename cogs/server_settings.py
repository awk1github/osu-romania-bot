import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedFactory


GUILD_ID = 1473125019692564542

DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "bot.db"
)


class ServerSettings(commands.Cog):
    server = app_commands.Group(
        name="server",
        description="Server configuration commands.",
        guild_ids=[GUILD_ID],
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ensure_database_columns()

    # --------------------------------------------------
    # DATABASE
    # --------------------------------------------------

    def ensure_database_columns(self) -> None:
        """
        Create guild_settings if it does not exist and add any
        missing server-setting columns.
        """

        DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    achievement_channel_id INTEGER,
                    achievements_enabled INTEGER NOT NULL DEFAULT 0,
                    autorole_id INTEGER,
                    autorole_enabled INTEGER NOT NULL DEFAULT 0,
                    welcome_channel_id INTEGER,
                    welcome_enabled INTEGER NOT NULL DEFAULT 0,
                    leave_channel_id INTEGER,
                    leave_enabled INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            cursor.execute(
                "PRAGMA table_info(guild_settings)"
            )

            existing_columns = {
                row[1]
                for row in cursor.fetchall()
            }

            required_columns = {
                "achievement_channel_id": "INTEGER",
                "achievements_enabled":
                    "INTEGER NOT NULL DEFAULT 0",
                "autorole_id": "INTEGER",
                "autorole_enabled":
                    "INTEGER NOT NULL DEFAULT 0",
                "welcome_channel_id": "INTEGER",
                "welcome_enabled":
                    "INTEGER NOT NULL DEFAULT 0",
                "leave_channel_id": "INTEGER",
                "leave_enabled":
                    "INTEGER NOT NULL DEFAULT 0",
            }

            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    cursor.execute(
                        f"""
                        ALTER TABLE guild_settings
                        ADD COLUMN {column_name} {column_type}
                        """
                    )

            connection.commit()

    def get_guild_settings(
        self,
        guild_id: int,
    ) -> sqlite3.Row | None:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    guild_id,
                    achievement_channel_id,
                    achievements_enabled,
                    autorole_id,
                    autorole_enabled,
                    welcome_channel_id,
                    welcome_enabled,
                    leave_channel_id,
                    leave_enabled
                FROM guild_settings
                WHERE guild_id = ?
                """,
                (guild_id,),
            )

            return cursor.fetchone()

    # --------------------------------------------------
    # ACHIEVEMENT CHANNEL
    # --------------------------------------------------

    @server.command(
        name="achievements",
        description="Configure achievement announcements.",
    )
    @app_commands.describe(
        channel=(
            "The achievement channel. "
            "Leave empty to disable announcements."
        )
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def achievements(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Server Only",
                    "This command can only be used inside a server.",
                ),
                ephemeral=True,
            )
            return

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            if channel is None:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        achievement_channel_id,
                        achievements_enabled
                    )
                    VALUES (?, NULL, 0)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        achievement_channel_id = NULL,
                        achievements_enabled = 0
                    """,
                    (interaction.guild.id,),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        achievement_channel_id,
                        achievements_enabled
                    )
                    VALUES (?, ?, 1)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        achievement_channel_id =
                            excluded.achievement_channel_id,
                        achievements_enabled = 1
                    """,
                    (
                        interaction.guild.id,
                        channel.id,
                    ),
                )

            connection.commit()

        if channel is None:
            embed = EmbedFactory.success(
                "Achievements Disabled",
                "Achievement announcements have been disabled.",
            )
        else:
            embed = EmbedFactory.success(
                "Achievement Channel Updated",
                (
                    "Achievement announcements will now be "
                    f"posted in {channel.mention}."
                ),
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # AUTOROLE
    # --------------------------------------------------

    @server.command(
        name="autorole",
        description="Configure the role given to new members.",
    )
    @app_commands.describe(
        role=(
            "The role given to new members. "
            "Leave empty to disable autorole."
        )
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Server Only",
                    "This command can only be used inside a server.",
                ),
                ephemeral=True,
            )
            return

        if role is not None:
            bot_member = guild.me

            if role.is_default():
                await interaction.response.send_message(
                    embed=EmbedFactory.error(
                        "Invalid Role",
                        "The `@everyone` role cannot be used as an autorole.",
                    ),
                    ephemeral=True,
                )
                return

            if role.managed:
                await interaction.response.send_message(
                    embed=EmbedFactory.error(
                        "Invalid Role",
                        "Managed integration roles cannot be assigned.",
                    ),
                    ephemeral=True,
                )
                return

            if (
                bot_member is None
                or role >= bot_member.top_role
            ):
                await interaction.response.send_message(
                    embed=EmbedFactory.error(
                        "Role Too High",
                        (
                            "That role is above or equal to my highest "
                            "role. Move my bot role above it first."
                        ),
                    ),
                    ephemeral=True,
                )
                return

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            if role is None:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        autorole_id,
                        autorole_enabled
                    )
                    VALUES (?, NULL, 0)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        autorole_id = NULL,
                        autorole_enabled = 0
                    """,
                    (guild.id,),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        autorole_id,
                        autorole_enabled
                    )
                    VALUES (?, ?, 1)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        autorole_id = excluded.autorole_id,
                        autorole_enabled = 1
                    """,
                    (
                        guild.id,
                        role.id,
                    ),
                )

            connection.commit()

        if role is None:
            embed = EmbedFactory.success(
                "Autorole Disabled",
                "New members will no longer receive an automatic role.",
            )
        else:
            embed = EmbedFactory.success(
                "Autorole Updated",
                f"New members will now receive {role.mention}.",
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # WELCOME CHANNEL
    # --------------------------------------------------

    @server.command(
        name="welcome",
        description="Configure welcome messages.",
    )
    @app_commands.describe(
        channel=(
            "The welcome channel. "
            "Leave empty to disable welcome messages."
        )
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Server Only",
                    "This command can only be used inside a server.",
                ),
                ephemeral=True,
            )
            return

        if (
            channel is not None
            and not channel.permissions_for(guild.me).send_messages
        ):
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Missing Channel Permission",
                    (
                        f"I cannot send messages in {channel.mention}. "
                        "Please update my channel permissions."
                    ),
                ),
                ephemeral=True,
            )
            return

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            if channel is None:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        welcome_channel_id,
                        welcome_enabled
                    )
                    VALUES (?, NULL, 0)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        welcome_channel_id = NULL,
                        welcome_enabled = 0
                    """,
                    (guild.id,),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        welcome_channel_id,
                        welcome_enabled
                    )
                    VALUES (?, ?, 1)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        welcome_channel_id =
                            excluded.welcome_channel_id,
                        welcome_enabled = 1
                    """,
                    (
                        guild.id,
                        channel.id,
                    ),
                )

            connection.commit()

        if channel is None:
            embed = EmbedFactory.success(
                "Welcome Messages Disabled",
                "Welcome messages have been disabled.",
            )
        else:
            embed = EmbedFactory.success(
                "Welcome Channel Updated",
                (
                    "Welcome messages will now be posted in "
                    f"{channel.mention}."
                ),
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # LEAVE CHANNEL
    # --------------------------------------------------

    @server.command(
        name="leave",
        description="Configure leave messages.",
    )
    @app_commands.describe(
        channel=(
            "The leave-message channel. "
            "Leave empty to disable leave messages."
        )
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def leave(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Server Only",
                    "This command can only be used inside a server.",
                ),
                ephemeral=True,
            )
            return

        if (
            channel is not None
            and not channel.permissions_for(guild.me).send_messages
        ):
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Missing Channel Permission",
                    (
                        f"I cannot send messages in {channel.mention}. "
                        "Please update my channel permissions."
                    ),
                ),
                ephemeral=True,
            )
            return

        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()

            if channel is None:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        leave_channel_id,
                        leave_enabled
                    )
                    VALUES (?, NULL, 0)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        leave_channel_id = NULL,
                        leave_enabled = 0
                    """,
                    (guild.id,),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO guild_settings (
                        guild_id,
                        leave_channel_id,
                        leave_enabled
                    )
                    VALUES (?, ?, 1)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        leave_channel_id =
                            excluded.leave_channel_id,
                        leave_enabled = 1
                    """,
                    (
                        guild.id,
                        channel.id,
                    ),
                )

            connection.commit()

        if channel is None:
            embed = EmbedFactory.success(
                "Leave Messages Disabled",
                "Leave messages have been disabled.",
            )
        else:
            embed = EmbedFactory.success(
                "Leave Channel Updated",
                (
                    "Leave messages will now be posted in "
                    f"{channel.mention}."
                ),
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # MEMBER JOIN EVENT
    # --------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
    ) -> None:
        settings = self.get_guild_settings(member.guild.id)

        if settings is None:
            return

        # Autorole
        if (
            settings["autorole_enabled"]
            and settings["autorole_id"]
        ):
            role = member.guild.get_role(
                settings["autorole_id"]
            )

            if role is not None:
                bot_member = member.guild.me

                if (
                    bot_member is not None
                    and role < bot_member.top_role
                    and not role.managed
                ):
                    try:
                        await member.add_roles(
                            role,
                            reason="Server autorole",
                        )
                    except (
                        discord.Forbidden,
                        discord.HTTPException,
                    ):
                        pass

        # Welcome message
        if (
            settings["welcome_enabled"]
            and settings["welcome_channel_id"]
        ):
            channel = member.guild.get_channel(
                settings["welcome_channel_id"]
            )

            if isinstance(channel, discord.TextChannel):
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=(
                        f"Welcome to **{member.guild.name}**, "
                        f"{member.mention}!\n\n"
                        "We hope you enjoy your stay."
                    ),
                    color=discord.Color.green(),
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                embed.set_footer(
                    text=(
                        f"Member #{member.guild.member_count}"
                    )
                )

                try:
                    await channel.send(embed=embed)
                except (
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    pass

    # --------------------------------------------------
    # MEMBER LEAVE EVENT
    # --------------------------------------------------

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member,
    ) -> None:
        settings = self.get_guild_settings(member.guild.id)

        if settings is None:
            return

        if not (
            settings["leave_enabled"]
            and settings["leave_channel_id"]
        ):
            return

        channel = member.guild.get_channel(
            settings["leave_channel_id"]
        )

        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title="👋 Member Left",
            description=(
                f"**{member}** has left "
                f"**{member.guild.name}**."
            ),
            color=discord.Color.red(),
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        try:
            await channel.send(embed=embed)
        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            pass

    # --------------------------------------------------
    # ERROR HANDLER
    # --------------------------------------------------

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = (
                "You need the Administrator permission "
                "to use this command."
            )
        else:
            raise error

        embed = EmbedFactory.error(
            "Missing Permission",
            message,
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerSettings(bot))