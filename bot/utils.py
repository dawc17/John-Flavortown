from __future__ import annotations

from typing import Iterable

import discord


def format_seconds(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if not seconds:
        return "0 secs"
    if seconds < 60:
        return f"{seconds} secs"
    if seconds < 3600:
        mins = seconds // 60
        return f"{mins} min{'s' if mins != 1 else ''}"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    if mins > 0:
        return f"{hours} hr{'s' if hours != 1 else ''} {mins} min{'s' if mins != 1 else ''}"
    return f"{hours} hr{'s' if hours != 1 else ''}"


def clamp_page(page: int, total_pages: int) -> int:
    total = max(1, total_pages)
    return max(1, min(page, total))


def calculate_total_pages(total_items: int, per_page: int) -> int:
    if per_page <= 0:
        return 1
    return max(1, (total_items + per_page - 1) // per_page)


def build_error_embed(message: str, title: str = "Error") -> discord.Embed:
    embed = discord.Embed(title=title, description=message, color=discord.Color.red())
    return embed


def build_info_embed(title: str, description: str, color: discord.Color | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color or discord.Color.orange())
    return embed


def iter_chunked(items: Iterable, size: int):
    """Yield items in chunks of size."""
    chunk = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


async def send_error(
    interaction: discord.Interaction,
    message: str,
    *,
    title: str = "Error",
    ephemeral: bool = True,
) -> None:
    embed = build_error_embed(message, title=title)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
