"""Pure functions that build Apify actor run inputs from a typed target.

Each scraper now takes its own per-target input (URL, handle, query) instead
of derving everything from the competitor's brand name. The :class:`Target`
dataclass carries the user-provided value and how to interpret it.
"""
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urlparse

from app.models.competitor_target import (
    TARGET_TYPE_HANDLE,
    TARGET_TYPE_PAGE_NAME,
    TARGET_TYPE_QUERY,
    TARGET_TYPE_URL,
)


# ── Apify actor IDs ───────────────────────────────────────────────────────────

ACTOR_FACEBOOK_ADS_ID = "apify/facebook-ads-scraper"
ACTOR_WEBSITE_ID = "apify/website-content-crawler"
ACTOR_GOOGLE_SEARCH_ID = "apify/google-search-scraper"
ACTOR_INSTAGRAM_ID = "apify/instagram-scraper"
ACTOR_TIKTOK_ID = "clockworks/tiktok-scraper"
ACTOR_GOOGLE_PLACES_ID = "compass/crawler-google-places"


# ── Target dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Target:
    actor_key: str
    target_value: str
    target_type: str  # one of competitor_target.TARGET_TYPE_*


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_handle(value: str) -> str:
    """Normalize a social handle: strip @, whitespace, and any URL prefix."""
    raw = value.strip()
    if raw.startswith("@"):
        raw = raw[1:]
    if raw.startswith("http://") or raw.startswith("https://"):
        path = urlparse(raw).path or ""
        parts = [p for p in path.split("/") if p]
        if parts:
            raw = parts[0]
    return raw.strip("/")


def _ensure_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        return raw
    if not (raw.startswith("http://") or raw.startswith("https://")):
        raw = "https://" + raw
    return raw


# ── Per-actor input builders ──────────────────────────────────────────────────

def build_facebook_ads_input(target: Target) -> dict[str, Any]:
    """Meta Ad Library — by Page URL when given (precise), or keyword search.

    ``activeStatus`` enum is ``"" | "active" | "inactive"`` — empty string
    means "all statuses" (the actor rejects ``"all"``).
    """
    if target.target_type == TARGET_TYPE_URL:
        url = _ensure_url(target.target_value)
        return {
            "startUrls": [{"url": url}],
            "resultsLimit": 100,
            "activeStatus": "",
        }

    # Page-name or query keyword search
    query = quote_plus(target.target_value.strip())
    return {
        "startUrls": [
            {
                "url": (
                    "https://www.facebook.com/ads/library/"
                    "?active_status=all&ad_type=all&country=ALL"
                    f"&q={query}&search_type=keyword_unordered"
                )
            }
        ],
        "resultsLimit": 100,
        "activeStatus": "",
    }


def build_google_search_input(target: Target) -> dict[str, Any]:
    """Top organic SERP for the supplied query."""
    return {
        "queries": target.target_value.strip(),
        "resultsPerPage": 10,
        "maxPagesPerQuery": 1,
        "countryCode": "us",
        "languageCode": "en",
        "mobileResults": False,
    }


def build_website_input(target: Target) -> dict[str, Any]:
    """Crawl the competitor's site (capped to 30 pages, text + markdown)."""
    url = _ensure_url(target.target_value)
    return {
        "startUrls": [{"url": url}],
        "crawlerType": "cheerio",
        "maxCrawlPages": 30,
        "maxCrawlDepth": 2,
        "saveMarkdown": True,
        "saveHtml": False,
        "removeCookieWarnings": True,
        "expandIframes": False,
    }


def build_instagram_input(target: Target) -> dict[str, Any]:
    """Instagram — directly target a profile by handle or URL."""
    if target.target_type == TARGET_TYPE_URL:
        url = _ensure_url(target.target_value)
        return {
            "directUrls": [url],
            "resultsType": "details",
            "resultsLimit": 60,
            "addParentData": False,
        }

    handle = _strip_handle(target.target_value)
    return {
        "directUrls": [f"https://www.instagram.com/{handle}/"],
        "resultsType": "details",
        "resultsLimit": 60,
        "addParentData": False,
    }


def build_tiktok_input(target: Target) -> dict[str, Any]:
    """TikTok — pull a creator's profile + recent videos."""
    if target.target_type == TARGET_TYPE_URL:
        url = _ensure_url(target.target_value)
        return {
            "profiles": [url],
            "resultsPerPage": 60,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSubtitles": False,
            "proxyCountryCode": "None",
        }

    handle = _strip_handle(target.target_value)
    return {
        "profiles": [handle],
        "resultsPerPage": 60,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
        "proxyCountryCode": "None",
    }


def build_google_places_input(target: Target) -> dict[str, Any]:
    """Google Maps — search for places matching the query, with reviews."""
    return {
        "searchStringsArray": [target.target_value.strip()],
        "maxCrawledPlacesPerSearch": 15,
        "language": "en",
        "skipClosedPlaces": False,
        "scrapePlaceDetailPage": True,
        "includeWebResults": False,
        "maxReviews": 30,
    }


# ── Validation hints (for the API & UI) ───────────────────────────────────────

DEFAULT_TARGET_TYPES: dict[str, str] = {
    "facebook_ads": TARGET_TYPE_URL,
    "website": TARGET_TYPE_URL,
    "google_search": TARGET_TYPE_QUERY,
    "instagram": TARGET_TYPE_HANDLE,
    "tiktok": TARGET_TYPE_HANDLE,
    "google_places": TARGET_TYPE_QUERY,
}


ALLOWED_TARGET_TYPES: dict[str, tuple[str, ...]] = {
    "facebook_ads": (TARGET_TYPE_URL, TARGET_TYPE_PAGE_NAME, TARGET_TYPE_QUERY),
    "website": (TARGET_TYPE_URL,),
    "google_search": (TARGET_TYPE_QUERY,),
    "instagram": (TARGET_TYPE_HANDLE, TARGET_TYPE_URL),
    "tiktok": (TARGET_TYPE_HANDLE, TARGET_TYPE_URL),
    "google_places": (TARGET_TYPE_QUERY,),
}
