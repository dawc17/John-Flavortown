import requests

HACKATIME_BASE_URL = "https://hackatime.hackclub.com"

class HackatimeAPIError(Exception):
    pass

def _get_headers(api_key: str):
    if not api_key:
        raise HackatimeAPIError("No Hackatime key provided.")
    return {
        "Authorization": f"Bearer {api_key}",
    }

def get_time_today(api_key: str):
    # GET /api/hackatime/v1/users/current/statusbar/today
    url = f"{HACKATIME_BASE_URL}/api/hackatime/v1/users/current/statusbar/today"
    try:
        response = requests.get(url, headers=_get_headers(api_key))
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
             raise HackatimeAPIError("Invalid API key or unauthorized access.")
        raise HackatimeAPIError(f"Failed to fetch today's time: {str(e)}")

def get_stats(api_key: str, username: str):
    # GET /api/v1/users/{username}/stats
    url = f"{HACKATIME_BASE_URL}/api/v1/users/{username}/stats"
    try:
        response = requests.get(url, headers=_get_headers(api_key))
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        if isinstance(e, requests.HTTPError) and e.response.status_code == 401:
             raise HackatimeAPIError("Invalid API key or unauthorized access.")
        raise HackatimeAPIError(f"Failed to fetch stats: {str(e)}")
