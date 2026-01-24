"""
Login cog for secure API key authentication.

Users encrypt their API keys with a personal password. The bot stores only
the encrypted version, ensuring that even the bot operator cannot read keys.
"""

import time
import json
import functools

import discord
from discord import app_commands
from discord.ext import commands
import requests

from bot.crypto import encrypt_api_key, decrypt_api_key
from bot.storage import store_encrypted_key, get_encrypted_key, delete_user_key, user_has_key
from bot.api import API_BASE_URL

# keys stored only in ram
# SESSION_CACHE[user_id] = { "flavortown": { "key": ..., "expires": ... }, "hackatime": ... }
SESSION_CACHE: dict[int, dict] = {}
SESSION_TIMEOUT = 7200  # 2 hours

class BaseLoginModal(discord.ui.Modal):
    """Base modal for login."""
    
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

    async def do_encryption_and_store(self, interaction: discord.Interaction, api_key: str, service: str, metadata: dict = None):
        if self.password.value != self.password_confirm.value:
            await interaction.response.send_message(
                "Passwords don't match! Please try again.",
                ephemeral=True
            )
            return
        
        encrypted_key, salt = encrypt_api_key(api_key, self.password.value)
        
        meta_str = json.dumps(metadata) if metadata else None
        store_encrypted_key(interaction.user.id, service, encrypted_key, salt, meta_str)
        
        await interaction.response.send_message(
            f"**Logged in to {service.title()} successfully!**\n\n"
            "Your API key has been encrypted with your password and stored securely.\n"
            "**Remember your password** - you'll need it to use API commands.\n\n"
            "*The bot operator cannot read your API key.*",
            ephemeral=True
        )

class FlavortownLoginModal(BaseLoginModal, title="Login to Flavortown"):
    api_key = discord.ui.TextInput(
        label="Flavortown API Key",
        placeholder="Your Flavortown API key",
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key.value}",
                "Content-Type": "application/json",
                "X-Flavortown-Ext-9378": "true"
            }
            response = requests.get(f"{API_BASE_URL}/api/v1/users/me", headers=headers, timeout=10)
            if response.status_code == 404:
                 response = requests.get(f"{API_BASE_URL}/api/v1/users", headers=headers, timeout=10)

            response.raise_for_status()
        except requests.RequestException as e:
            if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
                await interaction.response.send_message("Invalid API key! Please check your key and try again.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Could not verify API key: {str(e)}", ephemeral=True)
            return

        await self.do_encryption_and_store(interaction, self.api_key.value, "flavortown")


class HackatimeLoginModal(BaseLoginModal, title="Login to Hackatime"):
    api_key = discord.ui.TextInput(
        label="Hackatime API Key",
        placeholder="Your Hackatime API key",
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )

    username = discord.ui.TextInput(
        label="Hackatime Username",
        placeholder="Your Hackatime username",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            headers = {"Authorization": f"Bearer {self.api_key.value}"}
            url = "https://hackatime.hackclub.com/api/hackatime/v1/users/current/statusbar/today"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 401:
                await interaction.response.send_message("Invalid API key! Please check your key and try again.", ephemeral=True)
                return
            response.raise_for_status()
        except requests.RequestException as e:
             await interaction.response.send_message(f"Could not verify API key: {str(e)}", ephemeral=True)
             return

        await self.do_encryption_and_store(
            interaction, 
            self.api_key.value, 
            "hackatime", 
            metadata={"username": self.username.value}
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
    
    def __init__(self, callback, service: str = "flavortown", cache_key: bool = True):
        super().__init__()
        self._callback = callback
        self._service = service
        self._cache_key = cache_key
    
    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=True)
        # attempt to decrypt the key
        stored = get_encrypted_key(interaction.user.id, self._service)
        if stored:
            encrypted_key, salt, metadata = stored
            decrypted_key = decrypt_api_key(encrypted_key, salt, self.password.value)
            if decrypted_key and self._cache_key:
                if interaction.user.id not in SESSION_CACHE:
                    SESSION_CACHE[interaction.user.id] = {}
                SESSION_CACHE[interaction.user.id][self._service] = {
                    "key": decrypted_key,
                    "metadata": json.loads(metadata) if metadata else {},
                    "expires": time.time() + SESSION_TIMEOUT
                }
        await self._callback(interaction, self.password.value)


class Login(commands.Cog):
    """Handles user authentication with encrypted API key storage."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="login", description="Store your API key (encrypted with your password)")
    @app_commands.choices(service=[
        app_commands.Choice(name="Flavortown", value="flavortown"),
        app_commands.Choice(name="Hackatime", value="hackatime")
    ])
    async def login(self, interaction: discord.Interaction, service: app_commands.Choice[str]):
        """Open the login modal to store an encrypted API key."""
        if service.value == "flavortown":
            await interaction.response.send_modal(FlavortownLoginModal())
        elif service.value == "hackatime":
            await interaction.response.send_modal(HackatimeLoginModal())
    
    @app_commands.command(name="logout", description="Remove your stored API key")
    @app_commands.choices(service=[
        app_commands.Choice(name="Flavortown", value="flavortown"),
        app_commands.Choice(name="Hackatime", value="hackatime"),
        app_commands.Choice(name="All", value="all")
    ])
    async def logout(self, interaction: discord.Interaction, service: app_commands.Choice[str]):
        """Delete the user's stored encrypted key and clear session cache."""
        clear_user_session(interaction.user.id)
        
        tgt = service.value if service.value != "all" else None
        
        if delete_user_key(interaction.user.id, tgt):
            await interaction.response.send_message(
                f"Your API key(s) for {service.name} have been deleted and session cleared.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No keys found to delete.",
                ephemeral=True
            )
    
    @app_commands.command(name="status", description="Check if you have a stored API key")
    async def status(self, interaction: discord.Interaction):
        """Check if the user has a stored key."""
        ft = user_has_key(interaction.user.id, "flavortown")
        ht = user_has_key(interaction.user.id, "hackatime")
        
        msg = []
        if ft: msg.append("- Flavortown: ✅ Stored")
        else: msg.append("- Flavortown: ❌ Not stored")
        
        if ht: msg.append("- Hackatime: ✅ Stored")
        else: msg.append("- Hackatime: ❌ Not stored")
        
        await interaction.response.send_message(
            "**API Key Status:**\n" + "\n".join(msg) + "\n\nUse `/login` to store keys.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Login(bot))


def clear_user_session(user_id: int) -> bool:
    """Clear a user's session from the cache."""
    if user_id in SESSION_CACHE:
        del SESSION_CACHE[user_id]
        return True
    return False


async def get_api_key_for_user(
    interaction: discord.Interaction,
    password: str | None = None,
    service: str = "flavortown"
) -> str | None:
    """
    Attempt to get a user's API key from cache or decrypt it.
    """
    user_id = interaction.user.id
    
    if user_id in SESSION_CACHE and service in SESSION_CACHE[user_id]:
        session = SESSION_CACHE[user_id][service]
        if time.time() < session["expires"]:
            session["expires"] = time.time() + SESSION_TIMEOUT
            return session["key"]
        else:
            del SESSION_CACHE[user_id][service]
            if not SESSION_CACHE[user_id]:
                del SESSION_CACHE[user_id]
    
    if password is None:
        return None
    
    stored = get_encrypted_key(user_id, service)
    if not stored:
        return None
    
    encrypted_key, salt, metadata = stored
    decrypted_key = decrypt_api_key(encrypted_key, salt, password)
    
    if decrypted_key:
        if user_id not in SESSION_CACHE:
            SESSION_CACHE[user_id] = {}
        SESSION_CACHE[user_id][service] = {
            "key": decrypted_key,
            "metadata": json.loads(metadata) if metadata else {},
            "expires": time.time() + SESSION_TIMEOUT
        }
    
    return decrypted_key

async def get_user_metadata(interaction: discord.Interaction, service: str):
    user_id = interaction.user.id
    if user_id in SESSION_CACHE and service in SESSION_CACHE[user_id]:
        return SESSION_CACHE[user_id][service].get("metadata", {})
    
    stored = get_encrypted_key(user_id, service)
    if stored:
        _, _, metadata = stored
        if metadata:
            return json.loads(metadata)
    return {}

def require_auth(service="flavortown"):
    """
    Decorator for commands that require API authentication.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not user_has_key(interaction.user.id, service):
                await interaction.response.send_message(
                    f"You need to log in to **{service.title()}** first! Use `/login`.",
                    ephemeral=True
                )
                return
            
            async def on_password(modal_interaction: discord.Interaction, password: str):
                api_key = await get_api_key_for_user(modal_interaction, password, service)
                if not api_key:
                    await modal_interaction.response.send_message(
                        "Incorrect password! Please try again.",
                        ephemeral=True
                    )
                    return
                await func(self, modal_interaction, *args, **kwargs)
            
            key = await get_api_key_for_user(interaction, None, service)
            if key:
                await func(self, interaction, *args, **kwargs)
            else:
                modal = UnlockModal(on_password, service=service)
                await interaction.response.send_modal(modal)
        
        return wrapper
    return decorator
