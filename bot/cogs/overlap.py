import discord
from discord import app_commands
from discord.ext import commands

class Overlap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="overlap",
        description="Compare your devlog activity with another user"
    )
    async def overlap(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.send_message(
            f"Overlap system online. Comparing with {user.display_name}",
            ephemeral=True
        )

# THIS MUST EXIST
async def setup(bot: commands.Bot):
    await bot.add_cog(Overlap(bot))
