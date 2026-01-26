import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import require_auth, get_api_key_for_user
from bot.api import get_self, get_project_by_id, create_project, update_project
from bot.errors import APIError, StorageError
from bot.utils import send_error, normalize_optional, require_non_empty, validate_url
from bot.cogs.views import ConfirmView
from bot.demo import is_demo_mode


class Projects(commands.Cog):
    """Project commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        if is_demo_mode():
            await send_error(interaction, "Demo mode is enabled. Project creation is disabled.")
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
        if is_demo_mode():
            await send_error(interaction, "Demo mode is enabled. Project updates are disabled.")
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
            title = normalize_optional(title)
            description = normalize_optional(description)
            repo_url = validate_url(repo_url, "repo_url")
            demo_url = validate_url(demo_url, "demo_url")
            readme_url = validate_url(readme_url, "readme_url")
        except ValueError as e:
            await send_error(interaction, str(e))
            return

        if not any([title, description, repo_url, demo_url, readme_url]):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Projects(bot))
