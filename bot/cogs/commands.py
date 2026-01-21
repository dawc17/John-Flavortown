"""
Command cogs for Flavortown Discord bot.

Contains stub commands for search, list, stats, and time functionality.
"""

import discord
from discord import app_commands
from discord.ext import commands


class Commands(commands.Cog):
    """General commands for Flavortown bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
    ):
        """Search for users or projects by query."""
        await interaction.response.send_message(
            f"Searching for {category.value}: {query}",
            ephemeral=True,
        )

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
    ):
        """List shop items or projects."""
        await interaction.response.send_message(
            f"Listing: {category.value}",
            ephemeral=True,
        )

    @app_commands.command(name="stats", description="Show your Flavortown stats")
    async def stats(self, interaction: discord.Interaction):
        """Show user's stats (stub)."""
        await interaction.response.send_message(
            "Stats command - will show total coding time, cookies, etc.",
            ephemeral=True,
        )

    @app_commands.command(name="time", description="Show your coding time today")
    async def time(self, interaction: discord.Interaction):
        """Show coding time today (stub)."""
        await interaction.response.send_message(
            "Time command - will show today's coding time",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
