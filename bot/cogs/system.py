import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from bot import __version__, BOT_START_TIME
from bot.cogs.login import require_auth, get_api_key_for_user
from bot.errors import HackatimeError, StorageError
from bot.hackatime import get_time_today
from bot.utils import send_error


class System(commands.Cog):
    """Health and time commands."""

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
        try:
            api_key = await get_api_key_for_user(interaction, service="hackatime")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
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


async def setup(bot: commands.Bot):
    await bot.add_cog(System(bot))
