from typing import TypedDict

from bot.http import _request
from bot.errors import HackatimeError

HACKATIME_BASE_URL = "https://hackatime.hackclub.com"


class HackatimeGrandTotal(TypedDict, total=False):
    text: str


class HackatimeTodayData(TypedDict, total=False):
    grand_total: HackatimeGrandTotal


class HackatimeTodayResponse(TypedDict, total=False):
    data: HackatimeTodayData


class HackatimeStatsResponse(TypedDict, total=False):
    data: dict

def _get_headers(api_key: str) -> dict[str, str]:
    if not api_key:
        raise HackatimeError("No Hackatime key provided.")
    return {
        "Authorization": f"Bearer {api_key}",
    }

def get_time_today(api_key: str) -> HackatimeTodayResponse:
    # GET /api/hackatime/v1/users/current/statusbar/today
    url = f"{HACKATIME_BASE_URL}/api/hackatime/v1/users/current/statusbar/today"
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch today", service="hackatime", error_class=HackatimeError)

def get_stats(api_key: str, username: str) -> HackatimeStatsResponse:
    # GET /api/v1/users/{username}/stats
    url = f"{HACKATIME_BASE_URL}/api/v1/users/{username}/stats"
    return _request("GET", url, headers=_get_headers(api_key), action="Fetch stats", service="hackatime", error_class=HackatimeError)
