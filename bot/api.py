from bot.http import HTTPAPIError, _request

API_BASE_URL = "https://flavortown.hackclub.com"

class APIError(HTTPAPIError):
  pass

def _get_headers(api_key: str):
  """Get headers for API requests using the provided API key."""
  if not api_key:
    raise APIError("Not logged in.")
  
  headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "X-Flavortown-Ext-9378": "true"
  }

  return headers

def get_users(api_key: str, page: int = 1, query: str = None):
  url = f"{API_BASE_URL}/api/v1/users"
  params = {"page": page}
  if query:
    params["query"] = query
  return _request("GET", url, headers=_get_headers(api_key), params=params, action="Fetch users", service="flavortown", error_class=APIError)
  
def get_user_by_id(api_key: str, user_id: int):
  url = f"{API_BASE_URL}/api/v1/users/{user_id}"
  try:
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch user", service="flavortown", error_class=APIError)
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"User with ID {user_id} not found!")
    raise
  
def get_shop(api_key: str):
  url = f"{API_BASE_URL}/api/v1/store"
  return _request("GET", url, headers=_get_headers(api_key), action="Fetch shop", service="flavortown", error_class=APIError)
  
def get_projects(api_key: str, page: int = 1, query: str = None):
  url = f"{API_BASE_URL}/api/v1/projects"
  params = {"page": page}
  if query:
    params["query"] = query
  return _request("GET", url, headers=_get_headers(api_key), params=params, action="Fetch projects", service="flavortown", error_class=APIError)
  
def get_project_by_id(api_key: str, project_id: int):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}"
  try:
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch project", service="flavortown", error_class=APIError)
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"Project with ID {project_id} not found!")
    raise

def get_self(api_key: str):
  url = f"{API_BASE_URL}/api/v1/users/me"
  return _request("GET", url, headers=_get_headers(api_key), action="Fetch profile", service="flavortown", error_class=APIError)

def get_project_devlogs(api_key: str, project_id: int, page: int = 1):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}/devlogs"
  params = {"page": page}
  try:
    return _request("GET", url, headers=_get_headers(api_key), params=params, action="Fetch devlogs", service="flavortown", error_class=APIError)
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"Project with ID {project_id} not found!")
    raise
