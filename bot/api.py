import time
import requests

API_BASE_URL = "https://flavortown.hackclub.com"

class APIError(Exception):
  pass


def _format_error(action: str, url: str, status: int | None, detail: str) -> str:
  status_text = str(status) if status is not None else "unknown"
  return f"{action} failed (status={status_text}) {detail} | url={url}"


def _request(method: str, url: str, api_key: str, *, params: dict | None = None, json: dict | None = None, timeout: int = 10, action: str = "Request"):
  headers = _get_headers(api_key)
  max_retries = 2
  backoffs = [0.5, 1.0]

  for attempt in range(max_retries + 1):
    try:
      response = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json,
        timeout=timeout,
      )

      if response.status_code in (502, 503, 504) and attempt < max_retries:
        time.sleep(backoffs[attempt])
        continue

      if response.status_code == 401:
        raise APIError(_format_error(action, url, 401, "Invalid API key or unauthorized access!"))

      response.raise_for_status()
      return response.json()
    except requests.HTTPError as e:
      status = e.response.status_code if e.response else None
      detail = e.response.text.strip() if e.response and e.response.text else str(e)
      raise APIError(_format_error(action, url, status, detail))
    except requests.RequestException as e:
      raise APIError(_format_error(action, url, None, str(e)))

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
  return _request("GET", url, api_key, params=params, action="Fetch users")
  
def get_user_by_id(api_key: str, user_id: int):
  url = f"{API_BASE_URL}/api/v1/users/{user_id}"
  try:
    return _request("GET", url, api_key, action="Fetch user")
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"User with ID {user_id} not found!")
    raise
  
def get_shop(api_key: str):
  url = f"{API_BASE_URL}/api/v1/store"
  return _request("GET", url, api_key, action="Fetch shop")
  
def get_projects(api_key: str, page: int = 1, query: str = None):
  url = f"{API_BASE_URL}/api/v1/projects"
  params = {"page": page}
  if query:
    params["query"] = query
  return _request("GET", url, api_key, params=params, action="Fetch projects")
  
def get_project_by_id(api_key: str, project_id: int):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}"
  try:
    return _request("GET", url, api_key, action="Fetch project")
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"Project with ID {project_id} not found!")
    raise

def get_self(api_key: str):
  url = f"{API_BASE_URL}/api/v1/users/me"
  return _request("GET", url, api_key, action="Fetch profile")

def get_project_devlogs(api_key: str, project_id: int, page: int = 1):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}/devlogs"
  params = {"page": page}
  try:
    return _request("GET", url, api_key, params=params, action="Fetch devlogs")
  except APIError as e:
    if "status=404" in str(e):
      raise APIError(f"Project with ID {project_id} not found!")
    raise
