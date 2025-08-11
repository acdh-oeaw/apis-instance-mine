import os
from functools import cache
from typing import Any, Dict, Optional

import httpx
from django.core.management.base import CommandError

TOKEN = os.getenv("APIS_API_TOKEN")
headers = {"Authorization": f"Token {TOKEN}", "Accept": "application/json"}
BASE_URL = os.getenv("APIS_BASE_URL", "https://mine.acdh-ch-dev.oeaw.ac.at")


def api_request(
    url: str,
    logger,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    follow_redirects: bool = True,
) -> Dict[str, Any]:
    """
    Make an API request with error handling and logging.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, etc.)
        params: Query parameters for the request
        follow_redirects: Whether to follow HTTP redirects

    Returns:
        The JSON response as a dictionary

    Raises:
        CommandError: If the request fails
    """
    try:
        logger.debug(f"Making {method} request to {url} with params {params}")

        if method.upper() == "GET":
            response = httpx.get(
                url,
                params=params,
                headers=headers,
                follow_redirects=follow_redirects,
                timeout=30.0,  # Add a reasonable timeout
            )
        else:
            # Add support for other methods if needed
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Check for HTTP errors
        response.raise_for_status()

        # Log successful response
        logger.debug(f"Received response from {url}: status {response.status_code}")

        return response.json()

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error {e.response.status_code} when accessing {url}: {e.response.text}"
        logger.error(error_msg)
        raise CommandError(error_msg)

    except httpx.RequestError as e:
        error_msg = f"Request error when accessing {url}: {str(e)}"
        logger.error(error_msg)
        raise CommandError(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error when accessing {url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise CommandError(error_msg)


@cache
def get_api_object(url: str, logger) -> dict:
    return api_request(url, logger)


@cache
def get_vocab(url: str, logger) -> list:
    res = []
    voc = get_api_object(url, logger)
    res.append(voc)
    while voc["parent_class"]:
        url_lst = url.split("/")
        voc = get_api_object(
            "/".join(url_lst[:-2] + [str(voc["parent_class"]["id"])]) + "/", logger
        )
        res.append(voc)
    return list(reversed(res))
