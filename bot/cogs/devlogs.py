import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import require_auth, get_api_key_for_user
from bot.api import create_devlog_with_attachments, list_devlogs, get_devlog_by_id, get_project_devlogs
from bot.errors import APIError, StorageError
from bot.utils import send_error, parse_media_urls, require_non_empty, clamp_page
from bot.demo import is_demo_mode
from bot.cogs.views import DevlogListView, ProjectDevlogListView


class Devlogs(commands.Cog):
    """Devlog commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
            await send_error(interaction, f"API error: {e}")

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
        if is_demo_mode():
            await send_error(interaction, "Demo mode is enabled. Devlog creation is disabled.")
            return

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
    await bot.add_cog(Devlogs(bot))
