from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord


PageCallback = Callable[[int], Awaitable[discord.Embed]]


class PaginationView(discord.ui.View):
    """
    Reusable Previous/Next paginator.

    The supplied callback receives a page number and must return
    the embed that should be displayed for that page.
    """

    def __init__(
        self,
        *,
        author_id: int,
        current_page: int,
        max_pages: int,
        callback: PageCallback,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)

        if max_pages < 1:
            raise ValueError("max_pages must be at least 1.")

        if not 1 <= current_page <= max_pages:
            raise ValueError(
                "current_page must be between 1 and max_pages."
            )

        self.author_id = author_id
        self.current_page = current_page
        self.max_pages = max_pages
        self.callback = callback

        self.message: discord.Message | None = None

        self.update_buttons()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id == self.author_id:
            return True

        await interaction.response.send_message(
            "Only the person who opened this menu can use these buttons.",
            ephemeral=True,
        )
        return False

    def update_buttons(self) -> None:
        on_first_page = self.current_page <= 1
        on_last_page = self.current_page >= self.max_pages

        self.first_button.disabled = on_first_page
        self.previous_button.disabled = on_first_page

        self.next_button.disabled = on_last_page
        self.last_button.disabled = on_last_page

    async def change_page(
        self,
        interaction: discord.Interaction,
        new_page: int,
    ) -> None:
        new_page = max(
            1,
            min(new_page, self.max_pages),
        )

        if new_page == self.current_page:
            await interaction.response.defer()
            return

        try:
            embed = await self.callback(new_page)

        except Exception as error:
            print(
                "[PAGINATION] Failed to build page "
                f"{new_page}: {type(error).__name__}: {error}"
            )

            await interaction.response.send_message(
                "An error occurred while loading that page.",
                ephemeral=True,
            )
            return

        self.current_page = new_page
        self.update_buttons()

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

    @discord.ui.button(
        emoji="⏮️",
        style=discord.ButtonStyle.secondary,
    )
    async def first_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        await self.change_page(
            interaction,
            1,
        )

    @discord.ui.button(
        emoji="◀️",
        style=discord.ButtonStyle.secondary,
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        await self.change_page(
            interaction,
            self.current_page - 1,
        )

    @discord.ui.button(
        emoji="▶️",
        style=discord.ButtonStyle.secondary,
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        await self.change_page(
            interaction,
            self.current_page + 1,
        )

    @discord.ui.button(
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
    )
    async def last_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        await self.change_page(
            interaction,
            self.max_pages,
        )

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is None:
            return

        try:
            await self.message.edit(view=self)

        except discord.HTTPException:
            pass

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        print(
            "[PAGINATION] View error: "
            f"{type(error).__name__}: {error}"
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                "An unexpected pagination error occurred.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "An unexpected pagination error occurred.",
                ephemeral=True,
            )