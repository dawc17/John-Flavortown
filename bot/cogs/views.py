import discord

from bot.api import (
    get_users,
    get_projects,
    get_shop,
    list_devlogs,
    get_project_devlogs,
)
from bot.errors import APIError
from bot.config import (
    PAGINATION_VIEW_TIMEOUT_SECONDS,
    SHOP_PAGE_SIZE,
    PROJECT_PAGE_SIZE,
    SEARCH_USERS_PAGE_SIZE,
    SEARCH_PROJECTS_PAGE_SIZE,
)
from bot.utils import send_error


class ConfirmView(discord.ui.View):
    def __init__(self, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.confirmed = False

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="Confirmed. Processing...", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)


class PaginationView(discord.ui.View):
    """Base pagination view with Previous/Next buttons."""

    def __init__(self, api_key: str, current_page: int, total_pages: int, timeout: float = PAGINATION_VIEW_TIMEOUT_SECONDS):
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
        try:
            embed = await self.get_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self._update_buttons()
        try:
            embed = await self.get_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        except APIError as e:
            await send_error(interaction, f"API error: {e}")


class DevlogListView(PaginationView):
    def __init__(self, api_key: str, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)

    async def get_embed(self, page: int) -> discord.Embed:
        data = list_devlogs(self.api_key, page=page)
        devlogs = data.get("devlogs", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")

        embed = discord.Embed(
            title="Devlogs",
            description=f"Total: {total_count} (Page {page})",
            color=discord.Color.blue()
        )

        if not devlogs:
            embed.description = "No devlogs found on this page."
            return embed

        for d in devlogs[:10]:
            body = (d.get("body") or "").strip()
            if len(body) > 120:
                body = body[:117] + "..."
            devlog_id = d.get("id", "unknown")
            embed.add_field(
                name=f"Devlog {devlog_id}",
                value=body or "No body",
                inline=False
            )
        return embed


class ProjectDevlogListView(PaginationView):
    def __init__(self, api_key: str, project_id: int, current_page: int, total_pages: int):
        super().__init__(api_key, current_page, total_pages)
        self.project_id = project_id

    async def get_embed(self, page: int) -> discord.Embed:
        data = get_project_devlogs(self.api_key, self.project_id, page=page)
        devlogs = data.get("devlogs", [])
        total_count = data.get("pagination", {}).get("total_count", "Unknown")

        embed = discord.Embed(
            title=f"Project {self.project_id} Devlogs",
            description=f"Total: {total_count} (Page {page})",
            color=discord.Color.blue()
        )

        if not devlogs:
            embed.description = "No devlogs found on this page."
            return embed

        for d in devlogs[:10]:
            body = (d.get("body") or "").strip()
            if len(body) > 120:
                body = body[:117] + "..."
            devlog_id = d.get("id", "unknown")
            embed.add_field(
                name=f"Devlog {devlog_id}",
                value=body or "No body",
                inline=False
            )
        return embed


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

        for user in items[:SEARCH_USERS_PAGE_SIZE]:
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

        for project in items[:SEARCH_PROJECTS_PAGE_SIZE]:
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
        self.per_page = SHOP_PAGE_SIZE

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

        for project in items[:PROJECT_PAGE_SIZE]:
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
