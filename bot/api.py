import requests

API_BASE_URL = "https://flavortown.hackclub.com"

class APIError(Exception):
  pass

def _get_headers():
  key = "tbd"
  if not key:
    raise APIError("Not logged in.")
  
  headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "X-Flavortown-Ext-9378": "true"
  }

  return headers

def get_users(page: int = 1, query: str = None):
  url = f"{API_BASE_URL}/api/v1/users"
  params = {"page": page}
  if query:
    params["query"] = query
  try:
    response = requests.get(url, headers=_get_headers(), params=params)
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch users! {str(e)}")
  
def get_user_by_id(user_id: int):
  url = f"{API_BASE_URL}/api/v1/users/{user_id}"
  try:
    response = requests.get(url, headers=_get_headers())
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 404:
      raise APIError(f"User with ID {user_id} not found!")
    raise APIError(f"Failed to fetch user! {str(e)}")
  
def get_shop():
  url = f"{API_BASE_URL}/api/v1/store"
  try:
    response = requests.get(url, headers=_get_headers())
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch shop data! {str(e)}")
  
def get_projects(page: int = 1, query: str = None):
  url = f"{API_BASE_URL}/api/v1/projects"
  params = {"page": page}
  if query:
    params["query"] = query
  try:
    response = requests.get(url, headers=_get_headers(), params=params)
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
      raise APIError("Invalid API key or unauthorized access!")
    raise APIError(f"Failed to fetch projects! {str(e)}")
  
def get_project_by_id(project_id: int):
  url = f"{API_BASE_URL}/api/v1/projects/{project_id}"
  try:
    response = requests.get(url, headers=_get_headers())
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    if isinstance(e, requests.HTTPError) and e.response.status_code == 404:
      raise APIError(f"Project with ID {project_id} not found!")
    raise APIError(f"Failed to fetch project! {str(e)}")