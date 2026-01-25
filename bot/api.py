from typing import TypedDict

from bot.http import _request
from bot.errors import APIError

API_BASE_URL = "https://flavortown.hackclub.com"


class Pagination(TypedDict, total=False):
  total_pages: int
  total_count: int


class UserSummary(TypedDict, total=False):
  id: int
  display_name: str
  cookies: int
  slack_id: str
  avatar: str
  devlog_seconds_total: int
  devlog_seconds_today: int
  project_ids: list[int]


class UsersResponse(TypedDict, total=False):
  users: list[UserSummary]
  pagination: Pagination


class ProjectSummary(TypedDict, total=False):
  id: int
  title: str
  description: str
  repo_url: str
  devlog_ids: list[int]


class ProjectsResponse(TypedDict, total=False):
  projects: list[ProjectSummary]
  pagination: Pagination


class DevlogItem(TypedDict, total=False):
  id: int
  body: str
  scrapbook_url: str


class ProjectDevlogsResponse(TypedDict, total=False):
  devlogs: list[DevlogItem]


class TicketCost(TypedDict, total=False):
  base_cost: int

class ProjectCreatePayload(TypedDict, total=False):
  title: str
  description: str
  repo_url: str
  demo_url: str
  readme_url: str

class ProjectUpdatePayload(TypedDict, total=False):
  title: str
  description: str
  repo_url: str
  demo_url: str
  readme_url: str

class DevlogCreatePayload(TypedDict, total=False):
  body: str
  duration_seconds: int
  media_urls: list[str]


class ShopItem(TypedDict, total=False):
  id: int
  name: str
  ticket_cost: TicketCost
  stock: int | None
  limited: bool

def _get_headers(api_key: str) -> dict[str, str]:
  """Get headers for API requests using the provided API key."""
  if not api_key:
    raise APIError("Not logged in.")
  
  headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "X-Flavortown-Ext-9378": "true"
  }

  return headers

def get_users(api_key: str, page: int = 1, query: str | None = None) -> UsersResponse:
  url = f"{API_BASE_URL}/api/v1/users"
  params = {"page": page}
  if query:
    params["query"] = query
  return _request("GET", url, headers=_get_headers(api_key), params=params, action="Fetch users", service="flavortown", error_class=APIError)
  
def get_user_by_id(api_key: str, user_id: int) -> UserSummary:
  url = f"{API_BASE_URL}/api/v1/users/{user_id}"
  try:
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch user", service="flavortown", error_class=APIError)
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"User with ID {user_id} not found!")
    raise
  
def get_shop(api_key: str) -> list[ShopItem]:
  url = f"{API_BASE_URL}/api/v1/store"
  return _request("GET", url, headers=_get_headers(api_key), action="Fetch shop", service="flavortown", error_class=APIError)
  
def get_projects(api_key: str, page: int = 1, query: str | None = None) -> ProjectsResponse:
  url = f"{API_BASE_URL}/api/v1/projects"
  params = {"page": page}
  if query:
    params["query"] = query
  return _request("GET", url, headers=_get_headers(api_key), params=params, action="Fetch projects", service="flavortown", error_class=APIError)
  
def get_project_by_id(api_key: str, project_id: int) -> ProjectSummary:
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}"
  try:
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch project", service="flavortown", error_class=APIError)
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"Project with ID {project_id} not found!")
    raise

def get_self(api_key: str) -> UserSummary:
  url = f"{API_BASE_URL}/api/v1/users/me"
  return _request("GET", url, headers=_get_headers(api_key), action="Fetch profile", service="flavortown", error_class=APIError)

def get_project_devlogs(api_key: str, project_id: int, page: int = 1) -> ProjectDevlogsResponse:
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}/devlogs"
  params = {"page": page}
  try:
    return _request("GET", url, headers=_get_headers(api_key), params=params, action="Fetch devlogs", service="flavortown", error_class=APIError)
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"Project with ID {project_id} not found!")
    raise

def create_project(
    api_key: str,
    title: str,
    description: str | None = None,
    repo_url: str | None = None,
    demo_url: str | None = None,
    readme_url: str | None = None
) -> ProjectSummary:
  url = f"{API_BASE_URL}/api/v1/projects"
  payload: ProjectCreatePayload = {"title": title}
  if description: payload["description"] = description
  if repo_url: payload["repo_url"] = repo_url
  if demo_url: payload["demo_url"] = demo_url
  if readme_url: payload["readme_url"] = readme_url
  return _request("POST", url, headers=_get_headers(api_key), json=payload, action="Create project", service="flavortown", error_class=APIError)

def update_project(
    api_key: str,
    project_id: int,
    title: str | None = None,
    description: str | None = None,
    repo_url: str | None = None,
    demo_url: str | None = None,
    readme_url: str | None = None
) -> ProjectSummary:
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}"
  payload: ProjectUpdatePayload = {}
  if title: payload["title"] = title
  if description: payload["description"] = description
  if repo_url: payload["repo_url"] = description
  if demo_url: payload["demo_url"] = demo_url
  if readme_url: payload["readme_url"] = readme_url
  if not payload:
    raise APIError("No fields provided for update.")
  return _request("PATCH", url, headers=_get_headers(api_key), json=payload, action="Update project", service="flavortown", error_class=APIError)

def create_devlog(
    api_key: str,
    project_id: int,
    body: str,
    duration_seconds: int,
    media_urls: list[str] | None = None
) -> DevlogItem:
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}/devlogs"
  payload: DevlogCreatePayload = {"body": body, "duration_seconds": duration_seconds}
  if media_urls:
    payload["media_urls"] = media_urls
  return _request("POST", url, headers=_get_headers(api_key), json=payload, action="Create devlog", service="flavortown", error_class=APIError)