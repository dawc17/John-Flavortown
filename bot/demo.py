from __future__ import annotations

from bot.config import DEMO_MODE, DEMO_API_KEY, DEMO_HACKATIME_API_KEY

_DEMO_MODE = DEMO_MODE


def is_demo_mode() -> bool:
    return _DEMO_MODE


def set_demo_mode(enabled: bool) -> None:
    global _DEMO_MODE
    _DEMO_MODE = enabled


def get_demo_api_key(service: str) -> str | None:
    if service == "hackatime":
        return DEMO_HACKATIME_API_KEY or DEMO_API_KEY
    return DEMO_API_KEY
