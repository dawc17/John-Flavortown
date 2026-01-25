import random
import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import require_auth, get_api_key_for_user
from bot.api import get_users, get_user_by_id, get_self
from bot.errors import APIError, StorageError
from bot.utils import format_seconds, send_error


def compare_bar(you: int, them: int, width: int = 10) -> str:
    """Create a visual comparison bar."""
    total = you + them
    if total == 0:
        return "▓" * (width // 2) + "░" * (width // 2)
    you_blocks = round((you / total) * width)
    them_blocks = width - you_blocks
    return "🟩" * you_blocks + "🟥" * them_blocks


class Overlap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="overlap",
        description="Compare your stats with a random Flavortown user"
    )
    @require_auth(service="flavortown")
    async def overlap(self, interaction: discord.Interaction):
        """Compare your stats with a random user."""
        try:
            api_key = await get_api_key_for_user(interaction, service="flavortown")
        except StorageError:
            await send_error(interaction, "Storage error. Please try again in a moment.")
            return
        if not api_key:
            await send_error(interaction, "Failed to retrieve API key.")
            return

        try:
            my_data = get_self(api_key)
            my_name = my_data.get("display_name", "You")
            my_cookies = my_data.get("cookies") or 0
            my_total_time = my_data.get("devlog_seconds_total") or 0
            my_today_time = my_data.get("devlog_seconds_today") or 0
            my_projects = len(my_data.get("project_ids", []))
            my_id = my_data.get("id")
            
            random_page = random.randint(1, 10)
            users_data = get_users(api_key, page=random_page)
            users_list = users_data.get("users", [])
            
            if not users_list:
                await send_error(interaction, "Could not find any users to compare with!")
                return
            
            other_users = [u for u in users_list if u.get("id") != my_id]
            if not other_users:
                other_users = users_list
            
            random_user = random.choice(other_users)
            
            their_data = get_user_by_id(api_key, random_user.get("id"))
            their_name = their_data.get("display_name", "Unknown")
            their_cookies = their_data.get("cookies") or 0
            their_total_time = their_data.get("devlog_seconds_total") or 0
            their_today_time = their_data.get("devlog_seconds_today") or 0
            their_projects = len(their_data.get("project_ids", []))
            their_avatar = their_data.get("avatar")
            
            embed = discord.Embed(
                title=f"{my_name} vs {their_name}",
                description="Who's been grinding harder?",
                color=discord.Color.orange()
            )
            
            cookie_bar = compare_bar(my_cookies, their_cookies)
            embed.add_field(
                name="🍪 Cookies",
                value=f"**{my_cookies}** {cookie_bar} **{their_cookies}**",
                inline=False
            )
            
            time_bar = compare_bar(my_total_time, their_total_time)
            embed.add_field(
                name="Total Devlog Time",
                value=f"**{format_seconds(my_total_time)}** {time_bar} **{format_seconds(their_total_time)}**",
                inline=False
            )
            
            today_bar = compare_bar(my_today_time, their_today_time)
            embed.add_field(
                name="Devlog Time Today",
                value=f"**{format_seconds(my_today_time)}** {today_bar} **{format_seconds(their_today_time)}**",
                inline=False
            )
            
            proj_bar = compare_bar(my_projects, their_projects)
            embed.add_field(
                name="Projects",
                value=f"**{my_projects}** {proj_bar} **{their_projects}**",
                inline=False
            )
            
            your_score = 0
            their_score = 0
            if my_cookies > their_cookies: your_score += 1
            elif their_cookies > my_cookies: their_score += 1
            if my_total_time > their_total_time: your_score += 1
            elif their_total_time > my_total_time: their_score += 1
            if my_today_time > their_today_time: your_score += 1
            elif their_today_time > my_today_time: their_score += 1
            if my_projects > their_projects: your_score += 1
            elif their_projects > my_projects: their_score += 1
            
            if your_score > their_score:
                result = f"🏆 **{my_name}** wins! ({your_score}-{their_score})"
            elif their_score > your_score:
                result = f"😢 **{their_name}** wins! ({their_score}-{your_score})"
            else:
                result = f"It's a tie! ({your_score}-{their_score})"
            
            embed.add_field(name="Result", value=result, inline=False)
            
            if their_avatar:
                embed.set_thumbnail(url=their_avatar)
            
            embed.set_footer(text=f"🟩 = {my_name} | 🟥 = {their_name}")
            
            await interaction.response.send_message(embed=embed)
            
        except APIError as e:
            await send_error(interaction, f"API error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Overlap(bot))
