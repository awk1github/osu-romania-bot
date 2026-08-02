import discord
from discord import app_commands
from discord.ext import commands

import os
from dotenv import load_dotenv

import sqlite3
from datetime import datetime, timedelta

from utils.embeds import EmbedFactory


load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))


class Moderation(commands.Cog):
    mod = app_commands.Group(
        name="mod",
        description="Moderation commands.",
        guild_ids=[GUILD_ID],
    )
    
    warn_group = app_commands.Group(
        name="warn",
        description="Warning management commands.",
        parent=mod,
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_id = 1527677891888939089

    async def send_log(self, embed: discord.Embed):
        channel = self.bot.get_channel(self.log_channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    self.log_channel_id
                )
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            return

    async def log_action(
        self,
        action: str,
        moderator: discord.Member,
        target: discord.abc.User,
        color: discord.Color,
        reason: str | None = None,
        duration: str | None = None,
    ):
        embed = discord.Embed(
            title=action,
            color=color,
        )

        embed.add_field(
            name="Moderator",
            value=f"{moderator} ({moderator.id})",
            inline=False,
        )

        embed.add_field(
            name="Target",
            value=f"{target} ({target.id})",
            inline=False,
        )

        if reason:
            embed.add_field(
                name="Reason",
                value=reason,
                inline=False,
            )

        if duration:
            embed.add_field(
                name="Duration",
                value=duration,
                inline=False,
            )

        await self.send_log(embed)

    # --------------------------------------------------
    # PURGE
    # --------------------------------------------------

    @mod.command(
        name="purge",
        description="Delete messages.",
    )
    @app_commands.describe(
        amount="Number of messages to delete.",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ):
        if not isinstance(
            interaction.channel,
            (discord.TextChannel, discord.Thread),
        ):
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Invalid Channel",
                    "This command can only be used in a text channel or thread.",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(
                limit=amount
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Permission Error",
                    "I do not have permission to delete messages here.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Purge Failed",
                    "Discord could not delete the messages.",
                ),
                ephemeral=True,
            )
            return

        embed = EmbedFactory.success(
            "Messages Deleted",
            f"Deleted **{len(deleted)}** messages.",
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------

    @mod.command(
        name="timeout",
        description="Timeout a member.",
    )
    @app_commands.describe(
        member="The member to timeout.",
        minutes="Timeout duration in minutes.",
        reason="Reason for the timeout.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "No reason provided",
    ):
        if not await self.can_moderate_member(
            interaction,
            member,
        ):
            return

        await interaction.response.defer()

        try:
            await member.timeout(
                timedelta(minutes=minutes),
                reason=f"{reason} | Moderator: {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Permission Error",
                    "I cannot timeout that member. Check my role position and permissions.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Timeout Failed",
                    "Discord could not timeout that member.",
                ),
                ephemeral=True,
            )
            return

        await self.log_action(
            action="⏰ Member Timed Out",
            moderator=interaction.user,
            target=member,
            color=discord.Color.yellow(),
            reason=reason,
            duration=f"{minutes} minutes",
        )

        embed = EmbedFactory.success(
            "Member Timed Out",
            f"{member.mention} has been timed out for "
            f"**{minutes}** minute(s).",
        )

        await interaction.followup.send(embed=embed)

    # --------------------------------------------------
    # UNTIMEOUT
    # --------------------------------------------------

    @mod.command(
        name="untimeout",
        description="Remove a member's timeout.",
    )
    @app_commands.describe(
        member="The member whose timeout should be removed.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        if not await self.can_moderate_member(
            interaction,
            member,
        ):
            return

        await interaction.response.defer()

        try:
            await member.timeout(
                None,
                reason=f"Timeout removed by {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Permission Error",
                    "I cannot remove that member's timeout.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Action Failed",
                    "Discord could not remove that timeout.",
                ),
                ephemeral=True,
            )
            return

        await self.log_action(
            action="✅ Timeout Removed",
            moderator=interaction.user,
            target=member,
            color=discord.Color.green(),
        )

        embed = EmbedFactory.success(
            "Timeout Removed",
            f"{member.mention} is no longer timed out.",
        )

        await interaction.followup.send(embed=embed)

    # --------------------------------------------------
    # KICK
    # --------------------------------------------------

    @mod.command(
        name="kick",
        description="Kick a member.",
    )
    @app_commands.describe(
        member="The member to kick.",
        reason="Reason for the kick.",
    )
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if not await self.can_moderate_member(
            interaction,
            member,
        ):
            return

        await interaction.response.defer()

        try:
            await member.kick(
                reason=f"{reason} | Moderator: {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Permission Error",
                    "I cannot kick that member. Check my role position and permissions.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Kick Failed",
                    "Discord could not kick that member.",
                ),
                ephemeral=True,
            )
            return

        await self.log_action(
            action="👢 Member Kicked",
            moderator=interaction.user,
            target=member,
            color=discord.Color.orange(),
            reason=reason,
        )

        embed = EmbedFactory.success(
            "Member Kicked",
            f"{member} was kicked.",
        )

        await interaction.followup.send(embed=embed)

    # --------------------------------------------------
    # BAN
    # --------------------------------------------------

    @mod.command(
        name="ban",
        description="Ban a member.",
    )
    @app_commands.describe(
        member="The member to ban.",
        reason="Reason for the ban.",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if not await self.can_moderate_member(
            interaction,
            member,
        ):
            return

        await interaction.response.defer()

        try:
            await member.ban(
                reason=f"{reason} | Moderator: {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Permission Error",
                    "I cannot ban that member. Check my role position and permissions.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Ban Failed",
                    "Discord could not ban that member.",
                ),
                ephemeral=True,
            )
            return

        await self.log_action(
            action="🔨 Member Banned",
            moderator=interaction.user,
            target=member,
            color=discord.Color.red(),
            reason=reason,
        )

        embed = EmbedFactory.success(
            "Member Banned",
            f"{member} was banned.",
        )

        await interaction.followup.send(embed=embed)

    # --------------------------------------------------
    # UNBAN
    # --------------------------------------------------

    @mod.command(
        name="unban",
        description="Unban a user by their Discord ID.",
    )
    @app_commands.describe(
        user_id="The Discord user ID to unban.",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
    ):
        await interaction.response.defer()

        try:
            parsed_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Invalid User ID",
                    "The user ID must contain only numbers.",
                ),
                ephemeral=True,
            )
            return

        try:
            user = await self.bot.fetch_user(parsed_user_id)
            await interaction.guild.unban(
                user,
                reason=f"Unbanned by {interaction.user}",
            )
        except discord.NotFound:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "User Not Found",
                    "That user does not exist or is not currently banned.",
                ),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Permission Error",
                    "I cannot unban that user.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Unban Failed",
                    "Discord could not unban that user.",
                ),
                ephemeral=True,
            )
            return

        await self.log_action(
            action="🔓 Member Unbanned",
            moderator=interaction.user,
            target=user,
            color=discord.Color.green(),
        )

        embed = EmbedFactory.success(
            "Member Unbanned",
            f"{user} has been unbanned.",
        )

        await interaction.followup.send(embed=embed)

        # --------------------------------------------------
    # WARNING: ADD
    # --------------------------------------------------

    @warn_group.command(
        name="add",
        description="Warn a member.",
    )
    @app_commands.describe(
        member="The member to warn.",
        reason="The reason for the warning.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def add_warning(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ):
        if not await self.can_moderate_member(interaction, member):
            return

        await interaction.response.defer()

        connection = sqlite3.connect("database/bot.db")

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO warnings
                    (user_id, moderator_id, reason, date)
                VALUES (?, ?, ?, ?)
                """,
                (
                    member.id,
                    interaction.user.id,
                    reason,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

            warning_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        await self.log_action(
            action="⚠️ Member Warned",
            moderator=interaction.user,
            target=member,
            color=discord.Color.orange(),
            reason=reason,
        )

        embed = EmbedFactory.success(
            "Member Warned",
            (
                f"{member.mention} has been warned.\n\n"
                f"**Warning ID:** {warning_id}\n"
                f"**Reason:** {reason}"
            ),
        )

        await interaction.followup.send(embed=embed)

    # --------------------------------------------------
    # WARNING: LIST
    # --------------------------------------------------

    @warn_group.command(
        name="list",
        description="View a member's warnings.",
    )
    @app_commands.describe(
        member="The member whose warnings should be displayed.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def list_warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        await interaction.response.defer(ephemeral=True)

        connection = sqlite3.connect("database/bot.db")

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id, moderator_id, reason, date
                FROM warnings
                WHERE user_id = ?
                ORDER BY id ASC
                """,
                (member.id,),
            )

            rows = cursor.fetchall()
        finally:
            connection.close()

        if not rows:
            embed = EmbedFactory.info(
                "No Warnings",
                f"{member.mention} has no warnings.",
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            description=f"Total warnings: **{len(rows)}**",
            color=discord.Color.orange(),
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        for warning_id, moderator_id, reason, date in rows:
            embed.add_field(
                name=f"Warning #{warning_id}",
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** <@{moderator_id}>\n"
                    f"**Date:** {date}"
                ),
                inline=False,
            )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # WARNING: REMOVE
    # --------------------------------------------------

    @warn_group.command(
        name="remove",
        description="Remove one warning by its ID.",
    )
    @app_commands.describe(
        warning_id="The ID of the warning to remove.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def remove_warning(
        self,
        interaction: discord.Interaction,
        warning_id: int,
    ):
        await interaction.response.defer(ephemeral=True)

        connection = sqlite3.connect("database/bot.db")

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT user_id, reason
                FROM warnings
                WHERE id = ?
                """,
                (warning_id,),
            )

            warning = cursor.fetchone()

            if warning is None:
                embed = EmbedFactory.error(
                    "Warning Not Found",
                    f"No warning with ID **{warning_id}** exists.",
                )

                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True,
                )
                return

            warned_user_id, warning_reason = warning

            cursor.execute(
                "DELETE FROM warnings WHERE id = ?",
                (warning_id,),
            )

            connection.commit()
        finally:
            connection.close()

        user = interaction.guild.get_member(warned_user_id)

        if user is None:
            try:
                user = await self.bot.fetch_user(warned_user_id)
            except discord.HTTPException:
                user = None

        target_text = (
            user.mention
            if user is not None
            else f"<@{warned_user_id}>"
        )

        if user is not None:
            await self.log_action(
                action="🗑️ Warning Removed",
                moderator=interaction.user,
                target=user,
                color=discord.Color.orange(),
                reason=(
                    f"Removed warning #{warning_id}: "
                    f"{warning_reason}"
                ),
            )

        embed = EmbedFactory.success(
            "Warning Removed",
            (
                f"Warning **#{warning_id}** was removed from "
                f"{target_text}."
            ),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # WARNING: CLEAR
    # --------------------------------------------------

    @warn_group.command(
        name="clear",
        description="Remove all warnings from a member.",
    )
    @app_commands.describe(
        member="The member whose warnings should be cleared.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def clear_warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        await interaction.response.defer(ephemeral=True)

        connection = sqlite3.connect("database/bot.db")

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM warnings
                WHERE user_id = ?
                """,
                (member.id,),
            )

            count = cursor.fetchone()[0]

            if count == 0:
                embed = EmbedFactory.info(
                    "No Warnings",
                    f"{member.mention} has no warnings to remove.",
                )

                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True,
                )
                return

            cursor.execute(
                """
                DELETE FROM warnings
                WHERE user_id = ?
                """,
                (member.id,),
            )

            connection.commit()
        finally:
            connection.close()

        await self.log_action(
            action="🧹 Warnings Cleared",
            moderator=interaction.user,
            target=member,
            color=discord.Color.green(),
            reason=f"Cleared {count} warning(s)",
        )

        embed = EmbedFactory.success(
            "Warnings Cleared",
            (
                f"Removed **{count}** warning(s) from "
                f"{member.mention}."
            ),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    async def can_moderate_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Server Only",
                    "This command can only be used inside a server.",
                ),
                ephemeral=True,
            )
            return False

        moderator = interaction.user

        if member == moderator:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Invalid Target",
                    "You cannot moderate yourself.",
                ),
                ephemeral=True,
            )
            return False

        if member == interaction.guild.owner:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Invalid Target",
                    "The server owner cannot be moderated.",
                ),
                ephemeral=True,
            )
            return False

        if (
            isinstance(moderator, discord.Member)
            and moderator != interaction.guild.owner
            and member.top_role >= moderator.top_role
        ):
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Role Hierarchy",
                    "You cannot moderate a member with an equal or higher role.",
                ),
                ephemeral=True,
            )
            return False

        bot_member = interaction.guild.me

        if bot_member is None or member.top_role >= bot_member.top_role:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Bot Role Hierarchy",
                    "My highest role must be above the target member's highest role.",
                ),
                ephemeral=True,
            )
            return False

        return True

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.MissingPermissions):
            embed = EmbedFactory.error(
                "Missing Permissions",
                "You do not have permission to use this command.",
            )
        elif isinstance(error, app_commands.CommandOnCooldown):
            embed = EmbedFactory.error(
                "Command on Cooldown",
                f"Try again in {error.retry_after:.1f} seconds.",
            )
        else:
            raise error

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))