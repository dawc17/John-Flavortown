from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import DEFAULT_TIMEZONE, DEFAULT_PUBLIC_OUTPUT, DEFAULT_SERVICE
from bot.errors import StorageError
from bot.storage import get_user_preferences, upsert_user_preferences
from bot.utils import send_error

ALLOWED_SERVICES = {"flavortown", "hackatime"}


class Settings(commands.Cog):
    """User preferences."""

    settings = app_commands.Group(name="settings", description="View or update preferences")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _validate_timezone(self, tz: str) -> str:
        try:
            ZoneInfo(tz)
        except ZoneInfoNotFoundError as e:
            raise ValueError("Invalid timezone. Use an IANA name like 'UTC' or 'America/New_York'.") from e
        return tz

    def _normalize_service(self, service: str) -> str:
        if service not in ALLOWED_SERVICES:
            raise ValueError("default_service must be 'flavortown' or 'hackatime'.")
        return service

    def _resolve_default_service(self) -> str:
        return DEFAULT_SERVICE if DEFAULT_SERVICE in ALLOWED_SERVICES else "flavortown"

    @settings.command(name="view", description="View your settings")
    async def settings_view(self, interaction: discord.Interaction):
        try:
            prefs = get_user_preferences(interaction.user.id)
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return

        timezone = prefs.get("timezone") if prefs else None
        public_output = prefs.get("public_output") if prefs else None
        default_service = prefs.get("default_service") if prefs else None

        tz_value = timezone or DEFAULT_TIMEZONE
        public_value = public_output if public_output is not None else DEFAULT_PUBLIC_OUTPUT
        service_value = default_service or self._resolve_default_service()

        embed = discord.Embed(title="Settings", color=discord.Color.blue())
        embed.add_field(name="Timezone", value=tz_value, inline=False)
        embed.add_field(name="Output visibility", value="Public" if public_value else "Private", inline=False)
        embed.add_field(name="Default service", value=service_value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings.command(name="update", description="Update your settings")
    @app_commands.choices(default_service=[
        app_commands.Choice(name="Flavortown", value="flavortown"),
        app_commands.Choice(name="Hackatime", value="hackatime"),
    ])
    async def settings_update(
        self,
        interaction: discord.Interaction,
        timezone: str | None = None,
        public_output: bool | None = None,
        default_service: app_commands.Choice[str] | None = None,
    ):
        if timezone is None and public_output is None and default_service is None:
            await send_error(interaction, "Provide at least one field to update.")
            return

        try:
            if timezone is not None:
                timezone = self._validate_timezone(timezone.strip())
            if default_service is not None:
                default_service_value = self._normalize_service(default_service.value)
            else:
                default_service_value = None
        except ValueError as e:
            await send_error(interaction, str(e))
            return

        try:
            existing = get_user_preferences(interaction.user.id) or {}
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return

        resolved_timezone = (
            timezone
            if timezone is not None
            else existing.get("timezone") or DEFAULT_TIMEZONE
        )
        resolved_public_output = (
            public_output
            if public_output is not None
            else existing.get("public_output")
            if existing.get("public_output") is not None
            else DEFAULT_PUBLIC_OUTPUT
        )
        resolved_default_service = (
            default_service_value
            if default_service_value is not None
            else existing.get("default_service") or self._resolve_default_service()
        )

        try:
            upsert_user_preferences(
                interaction.user.id,
                resolved_timezone,
                resolved_public_output,
                resolved_default_service,
            )
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return

        embed = discord.Embed(title="Settings Updated", color=discord.Color.green())
        embed.add_field(name="Timezone", value=resolved_timezone, inline=False)
        embed.add_field(name="Output visibility", value="Public" if resolved_public_output else "Private", inline=False)
        embed.add_field(name="Default service", value=resolved_default_service, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
