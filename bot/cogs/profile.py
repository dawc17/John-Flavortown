import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import require_auth, UnlockModal
from bot.storage import user_has_key
from bot.api import get_users, APIError


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="Show Flavortown dev profile"
    )
    async def profile(self, interaction: discord.Interaction):
        """Show profile - requires authentication."""
        if not user_has_key(interaction.user.id):
            await interaction.response.send_message(
                "You need to log in first! Use `/login` to store your API key.",
                ephemeral=True
            )
            return
        
        async def on_password(modal_interaction: discord.Interaction, password: str):
            from bot.cogs.login import get_api_key_for_user
            
            api_key = await get_api_key_for_user(modal_interaction, password)
            if not api_key:
                await modal_interaction.response.send_message(
                    "Incorrect password! Please try again.",
                    ephemeral=True
                )
                return
            
            try:
                data = get_users(api_key, page=1)
                user_count = len(data.get("users", []))
                
                embed = discord.Embed(
                    title="Flavortown Profile",
                    description="Your API key is working!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="API Status",
                    value=f"Connected - Found {user_count} users on page 1",
                    inline=False
                )
                embed.set_footer(text="Your API key was decrypted temporarily and is not stored in plaintext.")
                
                await modal_interaction.response.send_message(embed=embed, ephemeral=True)
            except APIError as e:
                await modal_interaction.response.send_message(
                    f"API Error: {e}",
                    ephemeral=True
                )
        
        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
