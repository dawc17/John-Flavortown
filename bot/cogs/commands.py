"""
Command cogs for Flavortown Discord bot.

Contains commands for search, list, stats, and time functionality.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from bot import __version__, BOT_START_TIME

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import require_auth, get_api_key_for_user, UnlockModal
from bot.storage import user_has_key
from bot.api import create_project, update_project, create_devlog, get_users, get_projects, get_shop, get_self, get_project_by_id
from bot.errors import APIError, HackatimeError, StorageError
from bot.hackatime import get_time_today
from bot.config import (
    PAGINATION_VIEW_TIMEOUT_SECONDS,
    SHOP_PAGE_SIZE,
    PROJECT_PAGE_SIZE,
    SEARCH_USERS_PAGE_SIZE,
    SEARCH_PROJECTS_PAGE_SIZE,
)
from bot.utils import (clamp_page, calculate_total_pages, send_error, 
                       parse_media_urls, validate_duration_seconds, normalize_optional, require_non_empty, validate_url
                       )

class ConfirmView(discord.ui.View):
    def __init__(self, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.confirmed = False
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="Confirmed. Processing...", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)

class PaginationView(discord.ui.View):
    """Base pagination view with Previous/Next buttons."""
    
    def __init__(self, api_key: str, current_page: int, total_pages: int, timeout: float = PAGINATION_VIEW_TIMEOUT_SECONDS):
        super().__init__(timeout=timeout)
        self.api_key = api_key
        self.current_page = current_page
        self.total_pages = total_pages
        self._update_buttons()
    
    def _update_buttons(self):
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages
        self.page_label.label = f"Page {self.current_page}/{self.total_pages}"
    
    async def get_embed(self, page: int) -> discord.Embed:
        """Override in subclass to generate embed for given page."""
        raise NotImplementedError
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self._update_buttons()
        try:
            embed = await self.get_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")
    
    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self._update_buttons()
        try:
            embed = await self.get_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")


class SearchUserView(PaginationView):
    def __init__(self, api_key: str, query: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.query = query
    
    async def get_embed(self, page: int) -> discord.Embed:
        data = get_users(self.api_key, page=page, query=self.query)
        items = data.get("users", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")
        
        embed = discord.Embed(
            title=f"User Search: '{self.query}'",
            description=f"Found {total_count} results (Page {page})",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.description = f"No users found matching '{self.query}'."
        
        for user in items[:SEARCH_USERS_PAGE_SIZE]:
            d_name = user.get("display_name") or "Unknown"
            c_count = user.get("cookies") if user.get("cookies") is not None else 0
            s_id = user.get("slack_id") or "N/A"
            
            embed.add_field(
                name=f"{d_name} (ID: {user.get('id')})",
                value=f"Slack: `{s_id}`\nCookies: {c_count}",
                inline=True
            )
        return embed


class SearchProjectView(PaginationView):
    def __init__(self, api_key: str, query: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.query = query
    
    async def get_embed(self, page: int) -> discord.Embed:
        data = get_projects(self.api_key, page=page, query=self.query)
        items = data.get("projects", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")
        
        embed = discord.Embed(
            title=f"Project Search: '{self.query}'",
            description=f"Found {total_count} results (Page {page})",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.description = f"No projects found matching '{self.query}'."
            
        for project in items[:SEARCH_PROJECTS_PAGE_SIZE]:
            title = project.get("title") or "Unknown"
            desc = project.get("description") or "-"
            if len(desc) > 100:
                desc = desc[:97] + "..."
            repo = project.get("repo_url") or "No repo"
            
            embed.add_field(
                name=f"{title} (ID: {project.get('id')})",
                value=f"{desc}\n[Repo]({repo})" if repo != "No repo" else desc,
                inline=False
            )
        return embed


class ShopListView(PaginationView):
    def __init__(self, api_key: str, items: list, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.items = items
        self.per_page = SHOP_PAGE_SIZE
    
    async def get_embed(self, page: int) -> discord.Embed:
        start_idx = (page - 1) * self.per_page
        end_idx = start_idx + self.per_page
        page_items = self.items[start_idx:end_idx]

        embed = discord.Embed(
            title="Flavortown Shop",
            description=f"Page {page} of {self.total_pages} ({len(self.items)} items total)",
            color=discord.Color.gold()
        )
        
        for item in page_items:
            name = item.get("name") or "Unknown"
            ticket_cost = item.get("ticket_cost", {})
            base_cost = ticket_cost.get("base_cost", "N/A")
            stock = item.get("stock")
            if stock is None:
                stock = "∞"
            is_limited = " (Limited)" if item.get("limited") else ""
            
            embed.add_field(
                name=f"{name}",
                value=f"Cost: {base_cost} | Stock: {stock}{is_limited}",
                inline=False
            )
        return embed


class ProjectListView(PaginationView):
    def __init__(self, api_key: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
    
    async def get_embed(self, page: int) -> discord.Embed:
        data = get_projects(self.api_key, page=page)
        items = data.get("projects", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")
        
        embed = discord.Embed(
            title="Flavortown Projects",
            description=f"Total Projects: {total_count} (Page {page})",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.description = "No projects found on this page."
        
        for project in items[:PROJECT_PAGE_SIZE]:
            title = project.get("title") or "Unknown"
            desc = project.get("description") or "-"
            if len(desc) > 80:
                desc = desc[:77] + "..."
            repo = project.get("repo_url") or "#"
            
            embed.add_field(
                name=f"{title}",
                value=f"{desc}\n[Code]({repo})",
                inline=False
            )
        return embed


class Commands(commands.Cog):
    """General commands for Flavortown bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _format_uptime(self, start_time: datetime) -> str:
        delta = datetime.now(timezone.utc) - start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    
    def _get_db_status(self) -> str:
        db_path = Path(__file__).resolve().parents[2] / "data" / "keys.db"
        if not db_path.exists():
            return "Missing (keys.db not found)"
        
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cur = conn.execute("PRAGMA quick_check;")
                result = cur.fetchone()
                if result and result[0] == "ok":
                    return "OK"
                return f"Check: {result[0] if result else 'unknown'}"
        except Exception as e:
            return f"Error: {type(e).__name__}"

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
                
                if page < 1: page = 1
                if page > total_pages: page = total_pages

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
        
        # no cached key, prompt for password
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

    @app_commands.command(name="health", description="Check the bot's health")
    async def health(self, interaction: discord.Interaction):
        """Show the bot's health"""
        uptime = self._format_uptime(BOT_START_TIME)
        db_status = self._get_db_status()

        embed = discord.Embed(
            title="Bot Health",
            color=discord.Color.green()
        )

        embed.add_field(name="Version", value=__version__, inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="DB Status", value=db_status, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="time", description="Show your coding time today")
    @require_auth(service="hackatime")
    async def time(self, interaction: discord.Interaction):
        """Show coding time today."""
        api_key = await get_api_key_for_user(interaction, service="hackatime")
        if not api_key:
             await interaction.response.send_message("Failed to retrieve API key.", ephemeral=True)
             return
        
        try:
            data = get_time_today(api_key)
            grand_total = data.get("data", {}).get("grand_total", {})
            text = grand_total.get("text", "0 secs")
            
            embed = discord.Embed(
                title="Hackatime Progress",
                description=f"You have coded for **{text}** today! ⏱️",
                color=discord.Color.purple()
            )
            await interaction.response.send_message(embed=embed)
        except HackatimeError as e:
            await send_error(interaction, f"Hackatime error: {e}")

    @app_commands.command(name="project-create", description="Create a Flavortown project")
    @require_auth(service="flavortown")
    async def project_create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str | None = None,
        repo_url: str | None = None,
        demo_url: str | None = None,
        readme_url: str | None = None,
    ):
        try:
            api_key = await get_api_key_for_user(interaction, service="flavortown")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if not api_key:
            await send_error(interaction, "Failed to retrieve API key.")
            return
        
        try:
            title = require_non_empty(title, "title")
            description = normalize_optional(description)
            repo_url = validate_url(repo_url, "repo_url")
            demo_url = validate_url(demo_url, "demo_url")
            readme_url = validate_url(readme_url, "readme_url")
        except ValueError as e:
            await send_error(interaction, str(e))
            return
        
        try:
            created = create_project(api_key, title, description, repo_url, demo_url, readme_url)
            proj_id = created.get("id", "unknown")
            proj_title = created.get("title", title)
            await interaction.response.send_message(f"Project created. ID: {proj_id}. Title: {proj_title}", ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
