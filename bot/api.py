import requests

API_BASE_URL = "https://flavortown.hackclub.com"

class APIError(Exception):
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
  try:
    response = requests.get(url, headers=_get_headers(api_key), params=params)
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch users! {str(e)}")
  
def get_user_by_id(api_key: str, user_id: int):
  url = f"{API_BASE_URL}/api/v1/users/{user_id}"
  try:
    response = requests.get(url, headers=_get_headers(api_key))
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 404:
      raise APIError(f"User with ID {user_id} not found!")
    raise APIError(f"Failed to fetch user! {str(e)}")
  
def get_shop(api_key: str):
  url = f"{API_BASE_URL}/api/v1/store"
  try:
    response = requests.get(url, headers=_get_headers(api_key))
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch shop data! {str(e)}")
  
def get_projects(api_key: str, page: int = 1, query: str = None):
  url = f"{API_BASE_URL}/api/v1/projects"
  params = {"page": page}
  if query:
    params["query"] = query
  try:
    response = requests.get(url, headers=_get_headers(api_key), params=params)
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch projects! {str(e)}")
  
def get_project_by_id(api_key: str, project_id: int):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}"
  try:
    response = requests.get(url, headers=_get_headers(api_key))
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 404:
      raise APIError(f"Project with ID {project_id} not found!")
    raise APIError(f"Failed to fetch project! {str(e)}")

def get_self(api_key: str):
  url = f"{API_BASE_URL}/api/v1/users/me"
  try:
    response = requests.get(url, headers=_get_headers(api_key))
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch your profile! {str(e)}")

def get_project_devlogs(api_key: str, project_id: int, page: int = 1):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}/devlogs"
  params = {"page": page}
  try:
    response = requests.get(url, headers=_get_headers(api_key), params=params)
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 404:
      raise APIError(f"Project with ID {project_id} not found!")
    raise APIError(f"Failed to fetch devlogs! {str(e)}")
