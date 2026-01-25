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
from bot.api import create_project, update_project, create_devlog, create_devlog_with_attachments, get_self, get_project_by_id, get_devlog_by_id, get_users, get_projects, get_shop, list_devlogs, get_project_devlogs
from bot.errors import APIError, HackatimeError, StorageError
from bot.hackatime import get_time_today
from bot.config import SHOP_PAGE_SIZE
from bot.utils import (clamp_page, calculate_total_pages, send_error, 
                       parse_media_urls, normalize_optional, require_non_empty, validate_url
                       )
from bot.cogs.views import (
    ConfirmView,
    PaginationView,
    DevlogListView,
    ProjectDevlogListView,
    SearchUserView,
    SearchProjectView,
    ShopListView,
    ProjectListView,
)



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

    @app_commands.command(name="devlog-list", description="List recent devlogs")
    @require_auth(service="flavortown")
    async def devlog_list(self, interaction: discord.Interaction, page: int = 1):
        try:
            api_key = await get_api_key_for_user(interaction, service="flavortown")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if not api_key:
            await send_error(interaction, "Failed to retrieve API key.")
            return

        try:
            data = list_devlogs(api_key, page=page)
            pagination = data.get("pagination", {})
            total_pages = pagination.get("total_pages", 1) or 1
            page = clamp_page(page, total_pages)

            view = DevlogListView(api_key, page, total_pages)
            embed = await view.get_embed(page)

            if total_pages <= 1:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True) 
        except APIError as e:
            await send_error(interaction, f"API error {e}")

    @app_commands.command(name="devlog-view", description="View a devlog by ID")
    @require_auth(service="flavortown")
    async def devlog_view(self, interaction: discord.Interaction, devlog_id: int):
        try:
            api_key = await get_api_key_for_user(interaction, service="flavortown")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if not api_key:
            await send_error(interaction, "Failed to retrieve API key.")
            return
        
        try:
            data = get_devlog_by_id(api_key, devlog_id)
            devlog = data.get("devlog") or {}

            body = (devlog.get("body") or "").strip()
            scrapbook = devlog.get("scrapbook_url")

            embed = discord.Embed(
                title=f"Devlog {devlog_id}",
                description=body or "No body",
                color=discord.Color.blue()
            )

            if scrapbook:
                embed.add_field(name="Scrapbook", value=scrapbook, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    @app_commands.command(name="project-devlogs", description="List devlogs for a project")
    @require_auth(service="flavortown")
    async def project_devlogs(self, interaction: discord.Interaction, project_id: int, page: int = 1):
        try:
            api_key = await get_api_key_for_user(interaction, service="flavortown")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if not api_key:
            await send_error(interaction, "Failed to retrieve API key.")
            return

        try:
            data = get_project_devlogs(api_key, project_id, page=page)
            pagination = data.get("pagination", {})
            total_pages = pagination.get("total_pages", 1) or 1
            page = clamp_page(page, total_pages)

            view = ProjectDevlogListView(api_key, project_id, page, total_pages)
            embed = await view.get_embed(page)

            if total_pages <= 1:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    @app_commands.command(name="project-mine", description="List your own projects")
    @require_auth(service="flavortown")
    async def project_mine(self, interaction: discord.Interaction):
        try:
            api_key = await get_api_key_for_user(interaction, service="flavortown")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if not api_key:
            await send_error(interaction, "Failed to retrieve API key.")
            return

        try:
            me = get_self(api_key)
            project_ids = me.get("project_ids", [])
            if not project_ids:
                await send_error(interaction, "No projects found for your account.")
                return

            embed = discord.Embed(
                title="Your Projects",
                description=f"Total: {len(project_ids)}",
                color=discord.Color.blue()
            )

            for pid in project_ids[:20]:
                try:
                    project = get_project_by_id(api_key, pid)
                    title = project.get("title", "Unknown")
                    embed.add_field(name=f"{title} (ID: {pid})", value=project.get("description") or "-", inline=False)
                except APIError:
                    continue

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

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

    @app_commands.command(name="project-update", description="Update a Flavortown project")
    @require_auth(service="flavortown")
    async def project_update(
        self,
        interaction: discord.Interaction,
        project_id: int,
        title: str | None = None,
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
            title = normalize_optional(title)
            description = normalize_optional(description)
            repo_url = validate_url(repo_url, "repo_url")
            demo_url = validate_url(demo_url, "demo_url")
            readme_url = validate_url(readme_url, "readme_url")
        except ValueError as e:
            await send_error(interaction, str(e))
            return
        
        if not any ([title, description, repo_url, demo_url, readme_url]):
            await send_error(interaction, "Provide at least one field to update.")
            return
        
        try:
            me = get_self(api_key)
            project = get_project_by_id(api_key, project_id)
            owner_id = project.get("owner_id") or project.get("user_id") or project.get("creator_id")
            if owner_id is not None and me.get("id") != owner_id:
                await send_error(interaction, "You can only update your own projects.")
                return
        except APIError as e:
            await send_error(interaction, f"API error: {e}")
            return
        
        view = ConfirmView()
        await interaction.response.send_message(
            "Confirm update. This will overwrite the provided fields.",
            view=view,
            ephemeral=True
        )
        await view.wait()
        if not view.confirmed:
            return
        
        try:
            updated = update_project(api_key, project_id, title, description, repo_url, demo_url, readme_url)
            proj_title = updated.get("title", "unknown")
            await interaction.followup.send(f"Project updated. ID: {project_id}. Title: {proj_title}", ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    @app_commands.command(name="devlog-create", description="Create a devlog entry")
    @require_auth(service="flavortown")
    async def devlog_create(
        self,
        interaction: discord.Interaction,
        project_id: int,
        body: str,
        media_urls: str | None = None,
        attachment1: discord.Attachment | None = None,
        attachment2: discord.Attachment | None = None,
        attachment3: discord.Attachment | None = None,
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
            body = require_non_empty(body, "body")
            urls = parse_media_urls(media_urls)
        except ValueError as e:
            await send_error(interaction, str(e))
            return
        
        try:
            attachments = [a for a in [attachment1, attachment2, attachment3] if a is not None]
            file_payloads: list[tuple[str, bytes, str]] | None = None
            if attachments:
                file_payloads = []
                for attachment in attachments:
                    content = await attachment.read()
                    content_type = attachment.content_type or "application/octet-stream"
                    file_payloads.append((attachment.filename, content, content_type))

            created = create_devlog_with_attachments(
                api_key,
                project_id,
                body,
                urls,
                file_payloads,
            )
            devlog_id = created.get("id", "unknown")
            await interaction.response.send_message(f"Devlog created. ID: {devlog_id}", ephemeral=True)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
