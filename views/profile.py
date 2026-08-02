import discord

from utils.embeds import EmbedFactory
from utils.osu_api import OsuAPI
from utils.osu_embed import OsuEmbed
from utils.score_embed import ScoreEmbed


class ProfileView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        user: dict,
    ) -> None:
        super().__init__(timeout=180)

        self.author_id = author_id
        self.user = user
        self.osu_id = user["id"]

        self.current_tab = "profile"

        osu_profile_button = discord.ui.Button(
            label="osu! Profile",
            emoji="🔗",
            style=discord.ButtonStyle.link,
            url=f"https://osu.ppy.sh/users/{self.osu_id}",
        )

        self.add_item(osu_profile_button)

        self.update_buttons()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id == self.author_id:
            return True

        await interaction.response.send_message(
            "Only the person who used this command can use these buttons.",
            ephemeral=True,
        )

        return False

    def update_buttons(self) -> None:
        self.profile_button.disabled = (
            self.current_tab == "profile"
        )

        self.top_button.disabled = (
            self.current_tab == "top"
        )

        self.recent_button.disabled = (
            self.current_tab == "recent"
        )

    async def edit_tab(
        self,
        interaction: discord.Interaction,
        embed: discord.Embed,
        tab: str,
    ) -> None:
        self.current_tab = tab
        self.update_buttons()

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

    @discord.ui.button(
        label="Profile",
        emoji="👤",
        style=discord.ButtonStyle.primary,
    )
    async def profile_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        embed = OsuEmbed.profile(self.user)

        await self.edit_tab(
            interaction,
            embed,
            "profile",
        )

    @discord.ui.button(
        label="Top Plays",
        emoji="🏆",
        style=discord.ButtonStyle.secondary,
    )
    async def top_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.defer()

        scores = await OsuAPI.get_top(self.osu_id)

        if not scores:
            embed = EmbedFactory.info(
                "No Top Plays",
                (
                    f"No top plays were found for "
                    f"**{self.user['username']}**."
                ),
            )
        else:
            embed = ScoreEmbed.top(
                self.user,
                scores,
            )

        self.current_tab = "top"
        self.update_buttons()
        await interaction.edit_original_response(
            embed=embed,
            view=self,
        )

    @discord.ui.button(
        label="Recent Play",
        emoji="🕒",
        style=discord.ButtonStyle.secondary,
    )
    async def recent_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.defer()

        score = await OsuAPI.get_recent(self.osu_id)

        if score is None:
            embed = EmbedFactory.info(
                "No Recent Play",
                (
                    f"No recent play was found for "
                    f"**{self.user['username']}**."
                ),
            )
        else:
            score = await OsuAPI.enrich_score(score)
            embed = ScoreEmbed.recent(score)

        self.current_tab = "recent"
        self.update_buttons()

        await interaction.edit_original_response(
            embed=embed,
            view=self,
        )

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                if item.style != discord.ButtonStyle.link:
                    item.disabled = True
