"""
Turns a typed place ("Riverside, CA") into map coordinates using the public
OpenStreetMap Nominatim server.

Nominatim's usage policy (https://operations.osmfoundation.org/policies/nominatim/)
limits the WHOLE app to 1 request per second, requires an identifying
User-Agent, and forbids search-as-you-type. This module enforces that:
  - results are cached, so repeat searches never reach Nominatim
  - a shared 1-second gate in the database cache covers every gunicorn worker
  - the frontend only searches when the user presses Enter / Search
"""

import hashlib
import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
MAXIMUM_RESULTS = 5
REQUEST_TIMEOUT_SECONDS = 5
# Place coordinates rarely change, so a week of caching is safe
RESULT_CACHE_SECONDS = 60 * 60 * 24 * 7
RATE_GATE_CACHE_KEY = "place-search:nominatim-rate-gate"
RATE_GATE_SECONDS = 1


class PlaceSearchBusyError(Exception):
    """Another request used the 1-per-second Nominatim slot; try again shortly."""


class PlaceSearchUnavailableError(Exception):
    """Nominatim could not be reached or returned something unusable."""


def build_result_cache_key(search_text):
    # Same text with different capitalization/spacing shares one cache entry
    normalized_text = " ".join(search_text.lower().split())
    text_digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"place-search:result:{text_digest}"


def search_places(search_text):
    """
    Returns up to MAXIMUM_RESULTS places as
    [{"display_name": str, "latitude": float, "longitude": float}, ...]
    """
    result_cache_key = build_result_cache_key(search_text)
    cached_places = cache.get(result_cache_key)
    if cached_places is not None:
        return cached_places

    # cache.add only succeeds if the key is missing, so exactly one request
    # per second (across all workers) gets to call Nominatim
    if not cache.add(RATE_GATE_CACHE_KEY, True, timeout=RATE_GATE_SECONDS):
        raise PlaceSearchBusyError()

    query_parameters = {"q": search_text, "format": "jsonv2", "limit": MAXIMUM_RESULTS}
    # Blank setting means search worldwide, so leave the filter off entirely
    if settings.PLACE_SEARCH_COUNTRY_CODES:
        query_parameters["countrycodes"] = settings.PLACE_SEARCH_COUNTRY_CODES
    nominatim_request = Request(
        f"{NOMINATIM_SEARCH_URL}?{urlencode(query_parameters)}",
        headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
    )

    try:
        with urlopen(nominatim_request, timeout=REQUEST_TIMEOUT_SECONDS) as nominatim_response:
            raw_places = json.loads(nominatim_response.read().decode("utf-8"))
        # Nominatim sends lat/lon as strings; convert and keep only what the app uses
        places = [
            {
                "display_name": raw_place["display_name"],
                "latitude": float(raw_place["lat"]),
                "longitude": float(raw_place["lon"]),
            }
            for raw_place in raw_places
        ]
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as request_error:
        # Network failure, timeout, bad JSON, or an unexpected response shape
        raise PlaceSearchUnavailableError() from request_error

    cache.set(result_cache_key, places, timeout=RESULT_CACHE_SECONDS)
    return places
