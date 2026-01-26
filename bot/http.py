import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)
_SESSION = requests.Session()

_STATS = {
    "total_calls": 0,
    "error_calls": 0,
    "by_service": {},
}


def _track_call(service: str) -> None:
    _STATS["total_calls"] += 1
    _STATS["by_service"].setdefault(service, {"total": 0, "errors": 0})
    _STATS["by_service"][service]["total"] += 1


def _track_error(service: str) -> None:
    _STATS["error_calls"] += 1
    _STATS["by_service"].setdefault(service, {"total": 0, "errors": 0})
    _STATS["by_service"][service]["errors"] += 1


def get_http_stats() -> dict:
    return {
        "total_calls": _STATS["total_calls"],
        "error_calls": _STATS["error_calls"],
        "by_service": {k: v.copy() for k, v in _STATS["by_service"].items()},
    }


def reset_http_stats() -> None:
    _STATS["total_calls"] = 0
    _STATS["error_calls"] = 0
    _STATS["by_service"].clear()


class HTTPAPIError(Exception):
    pass


def _format_error(action: str, url: str, status: int | None, detail: str) -> str:
    status_text = str(status) if status is not None else "unknown"
    return f"{action} failed (status={status_text}) {detail} | url={url}"


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout: int = 10,
    action: str = "Request",
    service: str = "api",
    error_class: type[HTTPAPIError] = HTTPAPIError,
) -> Any:
    max_retries = 2
    backoffs = [0.5, 1.0]

    for attempt in range(max_retries + 1):
        try:
            _track_call(service)
            response = _SESSION.request(
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
                logger.error(
                    "event=api_error service=%s method=%s url=%s status=%s",
                    service,
                    method,
                    url,
                    response.status_code,
                )
                _track_error(service)
                raise error_class(_format_error(action, url, 401, "Invalid API key or unauthorized access."))

            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else None
            detail = e.response.text.strip() if e.response and e.response.text else str(e)
            logger.error(
                "event=api_error service=%s method=%s url=%s status=%s detail=%s",
                service,
                method,
                url,
                status,
                detail,
            )
            _track_error(service)
            raise error_class(_format_error(action, url, status, detail))
        except requests.RequestException as e:
            logger.error(
                "event=api_exception service=%s method=%s url=%s error=%s",
                service,
                method,
                url,
                str(e),
                exc_info=True,
            )
            _track_error(service)
            raise error_class(_format_error(action, url, None, str(e)))


def _request_multipart(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    data: dict[str, str] | list[tuple[str, str]],
    files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
    timeout: int = 10,
    action: str = "Request",
    service: str = "api",
    error_class: type[HTTPAPIError] = HTTPAPIError,
) -> Any:
    max_retries = 2
    backoffs = [0.5, 1.0]

    for attempt in range(max_retries + 1):
        try:
            _track_call(service)
            response = _SESSION.request(
                method,
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=timeout,
            )

            if response.status_code in (502, 503, 504) and attempt < max_retries:
                time.sleep(backoffs[attempt])
                continue

            if response.status_code == 401:
                logger.error(
                    "event=api_error service=%s method=%s url=%s status=%s",
                    service,
                    method,
                    url,
                    response.status_code,
                )
                _track_error(service)
                raise error_class(_format_error(action, url, 401, "Invalid API key or unauthorized access."))

            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else None
            detail = e.response.text.strip() if e.response and e.response.text else str(e)
            logger.error(
                "event=api_error service=%s method=%s url=%s status=%s detail=%s",
                service,
                method,
                url,
                status,
                detail,
            )
            _track_error(service)
            raise error_class(_format_error(action, url, status, detail))
        except requests.RequestException as e:
            logger.error(
                "event=api_exception service=%s method=%s url=%s error=%s",
                service,
                method,
                url,
                str(e),
                exc_info=True,
            )
            _track_error(service)
            raise error_class(_format_error(action, url, None, str(e)))
