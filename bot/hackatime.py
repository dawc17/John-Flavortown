from bot.http import HTTPAPIError, _request

HACKATIME_BASE_URL = "https://hackatime.hackclub.com"

class HackatimeAPIError(HTTPAPIError):
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
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch today", service="hackatime", error_class=HackatimeAPIError)

def get_stats(api_key: str, username: str):
    # GET /api/v1/users/{username}/stats
    url = f"{HACKATIME_BASE_URL}/api/v1/users/{username}/stats"
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch stats", service="hackatime", error_class=HackatimeAPIError)
