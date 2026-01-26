import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import ADMIN_USER_IDS
from bot.cogs.login import clear_all_sessions
from bot.http import get_http_stats, reset_http_stats
from bot.utils import send_error
from bot.demo import is_demo_mode, set_demo_mode, get_demo_api_key


class Admin(commands.Cog):
    """Admin tools."""

    admin = app_commands.Group(name="admin", description="Admin tools")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in ADMIN_USER_IDS:
            return True
        if interaction.guild and interaction.guild.owner_id == interaction.user.id:
            return True
        return False

    def _ensure_admin(self, interaction: discord.Interaction) -> bool:
        if not self._is_admin(interaction):
            return False
        return True

    @admin.command(name="cache-clear", description="Clear the session cache")
    async def cache_clear(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        removed = clear_all_sessions()
        await interaction.response.send_message(
            f"Cleared session cache ({removed} entries).",
            ephemeral=True,
        )

    @admin.command(name="stats", description="Show API call stats")
    async def stats(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        stats = get_http_stats()
        total_calls = stats["total_calls"]
        error_calls = stats["error_calls"]
        error_rate = (error_calls / total_calls * 100) if total_calls else 0.0

        embed = discord.Embed(title="API Stats", color=discord.Color.blurple())
        embed.add_field(name="Total calls", value=str(total_calls), inline=True)
        embed.add_field(name="Error calls", value=str(error_calls), inline=True)
        embed.add_field(name="Error rate", value=f"{error_rate:.2f}%", inline=True)

        by_service = stats.get("by_service", {})
        if by_service:
            lines = []
            for service, data in by_service.items():
                lines.append(f"- {service}: {data.get('total', 0)} calls, {data.get('errors', 0)} errors")
            embed.add_field(name="By service", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name="stats-reset", description="Reset API call stats")
    async def stats_reset(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        reset_http_stats()
        await interaction.response.send_message("API stats reset.", ephemeral=True)

    @admin.command(name="db-vacuum", description="Run VACUUM on the SQLite DB")
    async def db_vacuum(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        db_path = Path(__file__).resolve().parents[2] / "data" / "keys.db"
        if not db_path.exists():
            await send_error(interaction, "DB not found.")
            return

        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("VACUUM")
            await interaction.response.send_message("DB vacuum completed.", ephemeral=True)
        except sqlite3.Error:
            await send_error(interaction, "DB vacuum failed. Check logs.")

    @admin.command(name="demo-on", description="Enable demo mode")
    async def demo_on(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        set_demo_mode(True)
        ft_key = "set" if get_demo_api_key("flavortown") else "missing"
        ht_key = "set" if get_demo_api_key("hackatime") else "missing"
        await interaction.response.send_message(
            f"Demo mode enabled. Flavortown key: {ft_key}. Hackatime key: {ht_key}.",
            ephemeral=True,
        )

    @admin.command(name="demo-off", description="Disable demo mode")
    async def demo_off(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        set_demo_mode(False)
        await interaction.response.send_message("Demo mode disabled.", ephemeral=True)

    @admin.command(name="demo-status", description="Show demo mode status")
    async def demo_status(self, interaction: discord.Interaction):
        if not self._ensure_admin(interaction):
            await send_error(interaction, "You don't have permission to use this command.")
            return

        status = "enabled" if is_demo_mode() else "disabled"
        ft_key = "set" if get_demo_api_key("flavortown") else "missing"
        ht_key = "set" if get_demo_api_key("hackatime") else "missing"
        await interaction.response.send_message(
            f"Demo mode is {status}. Flavortown key: {ft_key}. Hackatime key: {ht_key}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
