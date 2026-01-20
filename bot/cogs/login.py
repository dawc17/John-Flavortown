"""
Login cog for secure API key authentication.

Users encrypt their API keys with a personal password. The bot stores only
the encrypted version, ensuring that even the bot operator cannot read keys.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.crypto import encrypt_api_key, decrypt_api_key
from bot.storage import store_encrypted_key, get_encrypted_key, delete_user_key, user_has_key
from bot.api import API_BASE_URL

import requests


class LoginModal(discord.ui.Modal, title="Login to Flavortown"):
    """Modal for users to enter their API key and password."""
    
    api_key = discord.ui.TextInput(
        label="API Key",
        placeholder="Your Flavortown API key",
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    password = discord.ui.TextInput(
        label="Encryption Password",
        placeholder="A password to encrypt your key (remember this!)",
        style=discord.TextStyle.short,
        required=True,
        min_length=8,
        max_length=100
    )
    
    password_confirm = discord.ui.TextInput(
        label="Confirm Password",
        placeholder="Enter the same password again",
        style=discord.TextStyle.short,
        required=True,
        min_length=8,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != self.password_confirm.value:
            await interaction.response.send_message(
                "Passwords don't match! Please try again.",
                ephemeral=True
            )
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key.value}",
                "Content-Type": "application/json",
                "X-Flavortown-Ext-9378": "true"
            }
            response = requests.get(f"{API_BASE_URL}/api/v1/users", headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
                await interaction.response.send_message(
                    "Invalid API key! Please check your key and try again.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Could not verify API key: {str(e)}",
                    ephemeral=True
                )
            return
        
        encrypted_key, salt = encrypt_api_key(self.api_key.value, self.password.value)
        store_encrypted_key(interaction.user.id, encrypted_key, salt)
        
        await interaction.response.send_message(
            "**Logged in successfully!**\n\n"
            "Your API key has been encrypted with your password and stored securely.\n"
            "**Remember your password** - you'll need it to use API commands.\n\n"
            "*The bot operator cannot read your API key.*",
            ephemeral=True
        )


class UnlockModal(discord.ui.Modal, title="Unlock API Access"):
    """Modal for users to enter their password to unlock API access."""
    
    password = discord.ui.TextInput(
        label="Your Encryption Password",
        placeholder="The password you used when logging in",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )
    
    def __init__(self, callback):
        super().__init__()
        self._callback = callback
    
    async def on_submit(self, interaction: discord.Interaction):
        await self._callback(interaction, self.password.value)


class Login(commands.Cog):
    """Handles user authentication with encrypted API key storage."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="login", description="Store your Flavortown API key (encrypted with your password)")
    async def login(self, interaction: discord.Interaction):
        """Open the login modal to store an encrypted API key."""
        modal = LoginModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="logout", description="Remove your stored API key")
    async def logout(self, interaction: discord.Interaction):
        """Delete the user's stored encrypted key."""
        if delete_user_key(interaction.user.id):
            await interaction.response.send_message(
                "Your API key has been deleted.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "You don't have a stored API key.",
                ephemeral=True
            )
    
    @app_commands.command(name="status", description="Check if you have a stored API key")
    async def status(self, interaction: discord.Interaction):
        """Check if the user has a stored key."""
        if user_has_key(interaction.user.id):
            await interaction.response.send_message(
                "You have an encrypted API key stored.\n"
                "Use commands that require API access and enter your password when prompted.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "You don't have an API key stored.\n"
                "Use `/login` to store your encrypted API key.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Login(bot))


# utility function for other cogs to get a decrypted API key
async def get_api_key_for_user(
    interaction: discord.Interaction,
    password: str
) -> str | None:
    """
    Attempt to decrypt and return a user's API key.
    
    Args:
        interaction: The Discord interaction (for user ID)
        password: The user's encryption password
    
    Returns:
        The decrypted API key, or None if decryption fails.
    """
    stored = get_encrypted_key(interaction.user.id)
    if not stored:
        return None
    
    encrypted_key, salt = stored
    return decrypt_api_key(encrypted_key, salt, password)


def require_auth(func):
    """
    Decorator for commands that require API authentication.
    
    Prompts the user for their password and passes the decrypted API key
    to the wrapped function.
    
    The wrapped function should have signature:
        async def cmd(self, interaction, api_key, *args, **kwargs)
    """
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        if not user_has_key(interaction.user.id):
            await interaction.response.send_message(
                "You need to log in first! Use `/login` to store your API key.",
                ephemeral=True
            )
            return
        
        async def on_password(modal_interaction: discord.Interaction, password: str):
            api_key = await get_api_key_for_user(modal_interaction, password)
            if not api_key:
                await modal_interaction.response.send_message(
                    "Incorrect password! Please try again.",
                    ephemeral=True
                )
                return
            
            await func(self, modal_interaction, api_key, *args, **kwargs)
        
        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
