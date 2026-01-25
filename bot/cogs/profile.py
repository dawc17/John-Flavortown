import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import UnlockModal, get_api_key_for_user
from bot.storage import user_has_key
from bot.api import get_self, get_project_by_id, get_project_devlogs
from bot.errors import APIError, StorageError
from bot.utils import format_seconds, send_error


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _flavor_rank(self, cookies: int, devlog_seconds_total: int) -> tuple[str, int, int]:
        score = max(0, cookies) + max(0, devlog_seconds_total // 3600)
        tiers = [
            (0, "Street Taco"),
            (25, "Food Truck"),
            (75, "Flame Griller"),
            (150, "Sauce Boss"),
            (300, "Mayor of Flavortown"),
        ]
        current = tiers[0]
        next_tier = None
        for i, tier in enumerate(tiers):
            if score >= tier[0]:
                current = tier
                next_tier = tiers[i + 1] if i + 1 < len(tiers) else None
        return current[1], score, (next_tier[0] if next_tier else current[0])

    def _progress_bar(self, value: int, max_value: int, length: int = 10) -> str:
        if max_value <= 0:
            return "░" * length
        filled = int(min(length, (value / max_value) * length))
        return "█" * filled + "░" * (length - filled)

    async def _show_profile(self, interaction: discord.Interaction, api_key: str):
        """Display a rich profile embed using the provided API key."""
        try:
            data = get_self(api_key)

            name = data.get("display_name") or "Unknown"
            cookies = data.get("cookies") if data.get("cookies") is not None else 0
            devlog_seconds_total = data.get("devlog_seconds_total") or 0
            devlog_seconds_today = data.get("devlog_seconds_today") or 0
            project_ids = data.get("project_ids", [])
            avatar_url = data.get("avatar")
            slack_id = data.get("slack_id")

            rank, score, next_threshold = self._flavor_rank(cookies, devlog_seconds_total)
            progress = self._progress_bar(score, max(next_threshold, 1))

            embed = discord.Embed(
                title=f"🍔 {name}'s Flavortown Profile",
                description=f"Rank: **{rank}**\n{progress} **{score}** XP",
                color=discord.Color.orange()
            )

            embed.add_field(name="Cookies", value=f"**{cookies}** 🍪", inline=True)
            embed.add_field(
                name="Devlog Time (Total)",
                value=f"**{format_seconds(devlog_seconds_total)}**",
                inline=True
            )
            embed.add_field(
                name="Devlog Time (Today)",
                value=f"**{format_seconds(devlog_seconds_today)}**",
                inline=True
            )

            embed.add_field(name="Projects", value=f"**{len(project_ids)}**", inline=True)
            if slack_id:
                embed.add_field(name="Slack", value=f"`{slack_id}`", inline=True)

            most_active_project = None
            max_devlogs = 0
            for pid in project_ids[:10]:
                try:
                    project = get_project_by_id(api_key, pid)
                    devlog_ids = project.get("devlog_ids", [])
                    if len(devlog_ids) > max_devlogs:
                        max_devlogs = len(devlog_ids)
                        most_active_project = project
                except APIError:
                    continue

            if most_active_project:
                project_title = most_active_project.get("title", "Unknown")
                embed.add_field(
                    name="Most Active Project",
                    value=f"**{project_title}** ({max_devlogs} devlogs)",
                    inline=False
                )

                try:
                    devlogs = get_project_devlogs(api_key, most_active_project.get("id"), page=1)
                    recent = (devlogs.get("devlogs") or [])
                    if recent:
                        recent_log = recent[0]
                        body = (recent_log.get("body") or "").strip()
                        if len(body) > 180:
                            body = body[:177] + "..."
                        scrapbook_url = recent_log.get("scrapbook_url")
                        if scrapbook_url:
                            body = f"{body}\n[View Scrapbook]({scrapbook_url})"
                        if body:
                            embed.add_field(name="Latest Devlog", value=body, inline=False)
                except APIError:
                    pass

            if avatar_url:
                embed.set_thumbnail(url=avatar_url)
            elif interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)

            embed.set_footer(text="Your API key was decrypted temporarily and is not stored in plaintext.")

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    @app_commands.command(
        name="profile",
        description="Show Flavortown dev profile"
    )
    async def profile(self, interaction: discord.Interaction):
        """Show profile - requires authentication."""
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
            await self._show_profile(interaction, api_key)
            return
        
        # no cached key, need to prompt for password
        async def on_password(modal_interaction: discord.Interaction, password: str):
            try:
                api_key = await get_api_key_for_user(modal_interaction, password)
            except StorageError:
                await send_error(modal_interaction, "Storage error. Please try again in a moment.")
                return
            if not api_key:
                if modal_interaction.response.is_done():
                    await modal_interaction.followup.send(
                        "Incorrect password! Please try again.",
                        ephemeral=True
                    )
                else:
                    await modal_interaction.response.send_message(
                        "Incorrect password! Please try again.",
                        ephemeral=True
                    )
                return
            
            await self._show_profile(modal_interaction, api_key)
        
        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
