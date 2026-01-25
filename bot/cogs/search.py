import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import get_api_key_for_user, UnlockModal
from bot.storage import user_has_key
from bot.api import get_users, get_projects, get_shop
from bot.errors import APIError, StorageError
from bot.config import SHOP_PAGE_SIZE
from bot.utils import clamp_page, calculate_total_pages, send_error
from bot.cogs.views import SearchUserView, SearchProjectView, ShopListView, ProjectListView


class Search(commands.Cog):
    """Search and list commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _do_search(self, interaction: discord.Interaction, api_key: str, category: str, query: str, page: int):
        """Execute the search with a valid API key."""
        try:
            if category == "users":
                requested_page = page
                data = get_users(api_key, page=page, query=query)
                items = data.get("users", [])
                pagination = data.get("pagination", {})
                total_pages = pagination.get("total_pages", 1) or 1
                page = clamp_page(page, total_pages)

                if page != requested_page:
                    data = get_users(api_key, page=page, query=query)
                    items = data.get("users", [])

                view = SearchUserView(api_key, query, page, total_pages)
                embed = await view.get_embed(page)

                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                requested_page = page
                data = get_projects(api_key, page=page, query=query)
                pagination = data.get("pagination", {})
                total_pages = pagination.get("total_pages", 1) or 1
                page = clamp_page(page, total_pages)

                if page != requested_page:
                    data = get_projects(api_key, page=page, query=query)

                view = SearchProjectView(api_key, query, page, total_pages)
                embed = await view.get_embed(page)

                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    async def _do_list(self, interaction: discord.Interaction, api_key: str, category: str, page: int):
        """Execute the list command with a valid API key."""
        try:
            if category == "shop":
                items = get_shop(api_key)
                if not items:
                    await interaction.response.send_message("No items found in the shop.", ephemeral=True)
                    return

                items.sort(key=lambda x: x.get("id", 0))

                total_items = len(items)
                total_pages = calculate_total_pages(total_items, SHOP_PAGE_SIZE)

                if page < 1:
                    page = 1
                if page > total_pages:
                    page = total_pages

                view = ShopListView(api_key, items, page, total_pages)
                embed = await view.get_embed(page)

                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            elif category == "projects":
                data = get_projects(api_key, page=page)
                pagination = data.get("pagination", {})
                total_pages = pagination.get("total_pages", 1)

                view = ProjectListView(api_key, page, total_pages)
                embed = await view.get_embed(page)

                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    @app_commands.command(name="search", description="Search for users or projects")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Users", value="users"),
            app_commands.Choice(name="Projects", value="projects"),
        ]
    )
    async def search(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        query: str,
        page: int = 1,
    ):
        """Search for users or projects by query."""
        try:
            if not user_has_key(interaction.user.id):
                await interaction.response.send_message(
                    "You need to log in first! Use `/login` to store your API key.",
                    ephemeral=True
                )
                return
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return

        try:
            api_key = await get_api_key_for_user(interaction)
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if api_key:
            await self._do_search(interaction, api_key, category.value, query, page)
            return

        async def on_password(modal_interaction: discord.Interaction, password: str):
            try:
                key = await get_api_key_for_user(modal_interaction, password)
            except StorageError:
                await send_error(modal_interaction, "Storage error. Please try again in a moment.")
                return
            if not key:
                await modal_interaction.response.send_message(
                    "Incorrect password! Please try again.",
                    ephemeral=True
                )
                return

            await self._do_search(modal_interaction, key, category.value, query, page)

        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="list", description="List shop items or projects")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Shop", value="shop"),
            app_commands.Choice(name="Projects", value="projects"),
        ]
    )
    async def list(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        page: int = 1,
    ):
        """List shop items or projects."""
        try:
            if not user_has_key(interaction.user.id):
                await interaction.response.send_message(
                    "You need to log in first! Use `/login` to store your API key.",
                    ephemeral=True
                )
                return
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return

        try:
            api_key = await get_api_key_for_user(interaction)
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if api_key:
            await self._do_list(interaction, api_key, category.value, page)
            return

        async def on_password(modal_interaction: discord.Interaction, password: str):
            try:
                key = await get_api_key_for_user(modal_interaction, password)
            except StorageError:
                await send_error(modal_interaction, "Storage error. Please try again in a moment.")
                return
            if not key:
                await modal_interaction.response.send_message(
                    "Incorrect password! Please try again.",
                    ephemeral=True
                )
                return
            await self._do_list(modal_interaction, key, category.value, page)

        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(Search(bot))
