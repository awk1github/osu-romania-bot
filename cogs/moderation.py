import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

from utils.embeds import EmbedFactory

GUILD_ID = 1473125019692564542

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1527677891888939089

    async def send_log(self, embed: discord.Embed):
        channel = self.bot.get_channel(self.log_channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    self.log_channel_id
                )
            except Exception:
                return

        await channel.send(embed=embed)

    async def log_action(
        self,
        action: str,
        moderator: discord.Member,
        target,
        color: discord.Color,
        reason: str = None,
        duration: str = None
    ):
        embed = discord.Embed(
            title=action,
            color=color
        )

        embed.add_field(
            name="Moderator",
            value=f"{moderator} ({moderator.id})",
            inline=False
        )

        embed.add_field(
            name="Target",
            value=f"{target} ({target.id})",
            inline=False
        )

        if reason:
            embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )

        if duration:
            embed.add_field(
                name="Duration",
                value=duration,
                inline=False
            )

        await self.send_log(embed)

    # --------------------------------------------------
    # PURGE
    # --------------------------------------------------

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="purge",
        description="Delete messages."
    )
    @app_commands.checks.has_permissions(
        manage_messages=True
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        deleted = await interaction.channel.purge(
            limit=amount
        )

        embed = EmbedFactory.success(
            "Messages Deleted",
            f"Deleted **{len(deleted)}** messages."
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    # --------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="timeout",
        description="Timeout a member."
    )
    @app_commands.default_permissions(moderate_members=True)

    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int,
        reason: str = "No reason provided"
    ):
        await interaction.response.defer()

        await member.timeout(
            timedelta(minutes=minutes),
            reason=reason
        )

        await self.log_action(
            action="⏰ Member Timed Out",
            moderator=interaction.user,
            target=member,
            color=discord.Color.yellow(),
            reason=reason,
            duration=f"{minutes} minutes"
        )

        embed = EmbedFactory.success(
            "Member Timed Out",
            f"{member.mention} has been timed out for **{minutes}** minute(s)."
        )

        await interaction.followup.send(
            embed=embed
        )

    # --------------------------------------------------
    # UNTIMEOUT
    # --------------------------------------------------

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="untimeout",
        description="Remove a timeout."
    )
    @app_commands.default_permissions(moderate_members=True)

    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        await interaction.response.defer()

        await member.timeout(None)

        await self.log_action(
            action="✅ Timeout Removed",
            moderator=interaction.user,
            target=member,
            color=discord.Color.green()
        )

        embed = EmbedFactory.success(
            "Timeout Removed",
            f"{member.mention} is no longer timed out."
        )

        await interaction.followup.send(
            embed=embed
        )

    # --------------------------------------------------
    # KICK
    # --------------------------------------------------

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="kick",
        description="Kick a member."
    )
    @app_commands.default_permissions(kick_members=True)

    @app_commands.checks.has_permissions(
        kick_members=True
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        await interaction.response.defer()

        await member.kick(reason=reason)

        await self.log_action(
            action="👢 Member Kicked",
            moderator=interaction.user,
            target=member,
            color=discord.Color.orange(),
            reason=reason
        )

        embed = EmbedFactory.success(
            "Member Kicked",
            f"{member} was kicked."
        )

        await interaction.followup.send(
            embed=embed
        )

    # --------------------------------------------------
    # BAN
    # --------------------------------------------------

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="ban",
        description="Ban a member."
    )
    @app_commands.default_permissions(ban_members=True)

    @app_commands.checks.has_permissions(
        ban_members=True
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        await interaction.response.defer()

        await member.ban(reason=reason)

        await self.log_action(
            action="🔨 Member Banned",
            moderator=interaction.user,
            target=member,
            color=discord.Color.red(),
            reason=reason
        )

        embed = EmbedFactory.success(
            "Member Banned",
            f"{member} was banned."
        )

        await interaction.followup.send(
            embed=embed
        )

    # --------------------------------------------------
    # UNBAN
    # --------------------------------------------------

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="unban",
        description="Unban a user."
    )
    @app_commands.default_permissions(ban_members=True)

    @app_commands.checks.has_permissions(
        ban_members=True
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        await interaction.response.defer()

        try:
            user = await self.bot.fetch_user(
                int(user_id)
            )

            await interaction.guild.unban(
                user
            )

            await self.log_action(
                action="🔓 Member Unbanned",
                moderator=interaction.user,
                target=user,
                color=discord.Color.green()
            )

            embed = EmbedFactory.success(
                "Member Unbanned",
                f"{user} has been unbanned."
            )

            await interaction.followup.send(
                embed=embed
            )

        except discord.NotFound:
            embed = EmbedFactory.error(
                "User Not Found",
                "No user with that ID exists."
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except discord.Forbidden:
            embed = EmbedFactory.error(
                "Permission Error",
                "I cannot unban that user."
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(
        Moderation(bot)
    )