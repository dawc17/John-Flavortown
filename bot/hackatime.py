import time
import requests

HACKATIME_BASE_URL = "https://hackatime.hackclub.com"

class HackatimeAPIError(Exception):
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
                raise HackatimeAPIError(_format_error(action, url, 401, "Invalid API key or unauthorized access."))

            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else None
            detail = e.response.text.strip() if e.response and e.response.text else str(e)
            raise HackatimeAPIError(_format_error(action, url, status, detail))
        except requests.RequestException as e:
            raise HackatimeAPIError(_format_error(action, url, None, str(e)))

def _get_headers(api_key: str):
    if not api_key:
        raise HackatimeAPIError("No Hackatime key provided.")
    return {
        "Authorization": f"Bearer {api_key}",
    }

def get_time_today(api_key: str):
    # GET /api/hackatime/v1/users/current/statusbar/today
    url = f"{HACKATIME_BASE_URL}/api/hackatime/v1/users/current/statusbar/today"
    return _request("GET", url, api_key, action="Fetch today")

def get_stats(api_key: str, username: str):
    # GET /api/v1/users/{username}/stats
    url = f"{HACKATIME_BASE_URL}/api/v1/users/{username}/stats"
    return _request("GET", url, api_key, action="Fetch stats")
