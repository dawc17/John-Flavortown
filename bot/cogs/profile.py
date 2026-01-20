import discord
from discord import app_commands
from discord.ext import commands

class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="Show Flavortown dev profile"
    )
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Profile system online.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
