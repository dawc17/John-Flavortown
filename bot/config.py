import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") else None

PAGINATION_VIEW_TIMEOUT_SECONDS = int(os.getenv("PAGINATION_VIEW_TIMEOUT_SECONDS", "180"))
SHOP_PAGE_SIZE = int(os.getenv("SHOP_PAGE_SIZE", "10"))
PROJECT_PAGE_SIZE = int(os.getenv("PROJECT_PAGE_SIZE", "20"))
SEARCH_USERS_PAGE_SIZE = int(os.getenv("SEARCH_USERS_PAGE_SIZE", "25"))
SEARCH_PROJECTS_PAGE_SIZE = int(os.getenv("SEARCH_PROJECTS_PAGE_SIZE", "20"))

DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "UTC")
DEFAULT_PUBLIC_OUTPUT = os.getenv("DEFAULT_PUBLIC_OUTPUT", "false").lower() in ("1", "true", "yes", "y", "on")
DEFAULT_SERVICE = os.getenv("DEFAULT_SERVICE", "flavortown")

_admin_ids_raw = os.getenv("ADMIN_USER_IDS", "").strip()
ADMIN_USER_IDS = {int(x) for x in _admin_ids_raw.split(",") if x.strip().isdigit()}