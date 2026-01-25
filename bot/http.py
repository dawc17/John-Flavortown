import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)
_SESSION = requests.Session()


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
            raise error_class(_format_error(action, url, None, str(e)))
