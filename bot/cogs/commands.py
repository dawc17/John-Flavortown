"""
Command cogs for Flavortown Discord bot.

Contains commands for search, list, stats, and time functionality.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.login import require_auth, get_api_key_for_user, UnlockModal
from bot.storage import user_has_key
from bot.api import get_users, get_projects, get_shop, get_self, get_project_by_id, APIError
from bot.hackatime import get_time_today, HackatimeAPIError


def format_seconds(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds} secs"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} min{'s' if mins != 1 else ''}"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if mins > 0:
            return f"{hours} hr{'s' if hours != 1 else ''} {mins} min{'s' if mins != 1 else ''}"
        return f"{hours} hr{'s' if hours != 1 else ''}"


class PaginationView(discord.ui.View):
    """Base pagination view with Previous/Next buttons."""
    
    def __init__(self, api_key: str, current_page: int, total_pages: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.api_key = api_key
        self.current_page = current_page
        self.total_pages = total_pages
        self._update_buttons()
    
    def _update_buttons(self):
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages
        self.page_label.label = f"Page {self.current_page}/{self.total_pages}"
    
    async def get_embed(self, page: int) -> discord.Embed:
        """Override in subclass to generate embed for given page."""
        raise NotImplementedError
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self._update_buttons()
        embed = await self.get_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self._update_buttons()
        embed = await self.get_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)


class SearchUserView(PaginationView):
    def __init__(self, api_key: str, query: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.query = query
    
    async def get_embed(self, page: int) -> discord.Embed:
        data = get_users(self.api_key, page=page, query=self.query)
        items = data.get("users", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")
        
        embed = discord.Embed(
            title=f"User Search: '{self.query}'",
            description=f"Found {total_count} results (Page {page})",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.description = f"No users found matching '{self.query}'."
        
        for user in items[:25]:
            d_name = user.get("display_name") or "Unknown"
            c_count = user.get("cookies") if user.get("cookies") is not None else 0
            s_id = user.get("slack_id") or "N/A"
            
            embed.add_field(
                name=f"{d_name} (ID: {user.get('id')})",
                value=f"Slack: `{s_id}`\nCookies: {c_count}",
                inline=True
            )
        return embed


class SearchProjectView(PaginationView):
    def __init__(self, api_key: str, query: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.query = query
    
    async def get_embed(self, page: int) -> discord.Embed:
        data = get_projects(self.api_key, page=page, query=self.query)
        items = data.get("projects", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")
        
        embed = discord.Embed(
            title=f"Project Search: '{self.query}'",
            description=f"Found {total_count} results (Page {page})",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.description = f"No projects found matching '{self.query}'."
            
        for project in items[:20]:
            title = project.get("title") or "Unknown"
            desc = project.get("description") or "-"
            if len(desc) > 100:
                desc = desc[:97] + "..."
            repo = project.get("repo_url") or "No repo"
            
            embed.add_field(
                name=f"{title} (ID: {project.get('id')})",
                value=f"{desc}\n[Repo]({repo})" if repo != "No repo" else desc,
                inline=False
            )
        return embed


class ShopListView(PaginationView):
    def __init__(self, api_key: str, items: list, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.items = items
        self.per_page = 10
    
    async def get_embed(self, page: int) -> discord.Embed:
        start_idx = (page - 1) * self.per_page
        end_idx = start_idx + self.per_page
        page_items = self.items[start_idx:end_idx]

        embed = discord.Embed(
            title="Flavortown Shop",
            description=f"Page {page} of {self.total_pages} ({len(self.items)} items total)",
            color=discord.Color.gold()
        )
        
        for item in page_items:
            name = item.get("name") or "Unknown"
            ticket_cost = item.get("ticket_cost", {})
            base_cost = ticket_cost.get("base_cost", "N/A")
            stock = item.get("stock")
            if stock is None:
                stock = "∞"
            is_limited = " (Limited)" if item.get("limited") else ""
            
            embed.add_field(
                name=f"{name}",
                value=f"Cost: {base_cost} | Stock: {stock}{is_limited}",
                inline=False
            )
        return embed


class ProjectListView(PaginationView):
    def __init__(self, api_key: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
    
    async def get_embed(self, page: int) -> discord.Embed:
        data = get_projects(self.api_key, page=page)
        items = data.get("projects", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")
        
        embed = discord.Embed(
            title="Flavortown Projects",
            description=f"Total Projects: {total_count} (Page {page})",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.description = "No projects found on this page."
        
        for project in items[:20]:
            title = project.get("title") or "Unknown"
            desc = project.get("description") or "-"
            if len(desc) > 80:
                desc = desc[:77] + "..."
            repo = project.get("repo_url") or "#"
            
            embed.add_field(
                name=f"{title}",
                value=f"{desc}\n[Code]({repo})",
                inline=False
            )
        return embed


class Commands(commands.Cog):
    """General commands for Flavortown bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _do_search(self, interaction: discord.Interaction, api_key: str, category: str, query: str, page: int):
        """Execute the search with a valid API key."""
        try:
            if category == "users":
                data = get_users(api_key, page=page, query=query)
                items = data.get("users", [])
                pagination = data.get("pagination", {})
                total_pages = pagination.get("total_pages", 1)
                
                view = SearchUserView(api_key, query, page, total_pages)
                embed = await view.get_embed(page)
                
                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            else:
                data = get_projects(api_key, page=page, query=query)
                pagination = data.get("pagination", {})
                total_pages = pagination.get("total_pages", 1)
                
                view = SearchProjectView(api_key, query, page, total_pages)
                embed = await view.get_embed(page)
                
                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except APIError as e:
            await interaction.response.send_message(
                f"API Error: {e}",
                ephemeral=True
            )

    async def _do_list(self, interaction: discord.Interaction, api_key: str, category: str, page: int):
        """Execute the list command with a valid API key."""
        try:
            if category == "shop":
                items = get_shop(api_key)
                if not items:
                    await interaction.response.send_message("No items found in the shop.", ephemeral=True)
                    return
                
                items.sort(key=lambda x: x.get("id", 0))

                PER_PAGE = 10
                total_items = len(items)
                total_pages = (total_items + PER_PAGE - 1) // PER_PAGE
                
                if page < 1: page = 1
                if page > total_pages: page = total_pages

                view = ShopListView(api_key, items, page, total_pages)
                embed = await view.get_embed(page)
                
                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            elif category == "projects":
                data = get_projects(api_key, page=page)
                pagination = data.get("pagination", {})
                total_pages = pagination.get("total_pages", 1)
                
                view = ProjectListView(api_key, page, total_pages)
                embed = await view.get_embed(page)
                
                if total_pages <= 1:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                
        except APIError as e:
            await interaction.response.send_message(
                f"API Error: {e}",
                ephemeral=True
            )

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
        page: int = 1,
    ):
        """Search for users or projects by query."""
        if not user_has_key(interaction.user.id):
            await interaction.response.send_message(
                "You need to log in first! Use `/login` to store your API key.",
                ephemeral=True
            )
            return

        api_key = await get_api_key_for_user(interaction)
        if api_key:
            await self._do_search(interaction, api_key, category.value, query, page)
            return
        
        # no cached key, prompt for password
        async def on_password(modal_interaction: discord.Interaction, password: str):
            key = await get_api_key_for_user(modal_interaction, password)
            if not key:
                await modal_interaction.response.send_message(
                    "Incorrect password! Please try again.",
                    ephemeral=True
                )
                return
            
            await self._do_search(modal_interaction, key, category.value, query, page)
        
        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)

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
        page: int = 1,
    ):
        """List shop items or projects."""
        if not user_has_key(interaction.user.id):
            await interaction.response.send_message(
                "You need to log in first! Use `/login` to store your API key.",
                ephemeral=True
            )
            return

        api_key = await get_api_key_for_user(interaction)
        if api_key:
            await self._do_list(interaction, api_key, category.value, page)
            return
        
        async def on_password(modal_interaction: discord.Interaction, password: str):
            key = await get_api_key_for_user(modal_interaction, password)
            if not key:
                await modal_interaction.response.send_message(
                    "Incorrect password! Please try again.",
                    ephemeral=True
                )
                return
            await self._do_list(modal_interaction, key, category.value, page)
        
        modal = UnlockModal(on_password)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="stats", description="Show your Flavortown stats")
    @require_auth(service="flavortown")
    async def stats(self, interaction: discord.Interaction):
        """Show user's stats."""
        api_key = await get_api_key_for_user(interaction, service="flavortown")
        if not api_key:
             await interaction.response.send_message("Failed to retrieve API key.", ephemeral=True)
             return

        try:
            data = get_self(api_key)
            name = data.get("display_name", "Unknown")
            cookies = data.get("cookies", 0)
            devlog_seconds_total = data.get("devlog_seconds_total", 0)
            devlog_seconds_today = data.get("devlog_seconds_today", 0)
            project_ids = data.get("project_ids", [])
            avatar_url = data.get("avatar")
            
            embed = discord.Embed(
                title=f"🍪 Stats for {name}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Cookies", value=f"**{cookies}** 🍪", inline=True)
            
            total_time_str = format_seconds(devlog_seconds_total) if devlog_seconds_total else "0 secs"
            embed.add_field(name="Total Devlog Time", value=f"**{total_time_str}** ⏱️", inline=True)
            
            today_time_str = format_seconds(devlog_seconds_today) if devlog_seconds_today else "0 secs"
            embed.add_field(name="Devlog Time Today", value=f"**{today_time_str}**", inline=True)
            
            if project_ids:
                most_worked_project = None
                max_devlog_time = 0
                
                for pid in project_ids[:10]:  # limit to avoid too many API calls
                    try:
                        project = get_project_by_id(api_key, pid)
                        devlog_ids = project.get("devlog_ids", [])
                        # estimate time by number of devlogs as a heuristic
                        if len(devlog_ids) > max_devlog_time:
                            max_devlog_time = len(devlog_ids)
                            most_worked_project = project
                    except APIError:
                        continue
                
                if most_worked_project:
                    project_title = most_worked_project.get("title", "Unknown")
                    embed.add_field(
                        name="Most Active Project",
                        value=f"**{project_title}** ({max_devlog_time} devlogs)",
                        inline=False
                    )
            
            if avatar_url:
                embed.set_thumbnail(url=avatar_url)
            elif interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            
            embed.set_footer(text=f"Projects: {len(project_ids)}")
            
            await interaction.response.send_message(embed=embed)
        except APIError as e:
            await interaction.response.send_message(f"Error fetching stats: {e}", ephemeral=True)

    @app_commands.command(name="time", description="Show your coding time today")
    @require_auth(service="hackatime")
    async def time(self, interaction: discord.Interaction):
        """Show coding time today."""
        api_key = await get_api_key_for_user(interaction, service="hackatime")
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
        except HackatimeAPIError as e:
            await interaction.response.send_message(f"Hackatime Error: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
