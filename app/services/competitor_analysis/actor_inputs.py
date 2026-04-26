"""Pure functions that build Apify actor run inputs from a brand name."""
from typing import Any


# ── Apify actor IDs ───────────────────────────────────────────────────────────

ACTOR_FACEBOOK_ADS_ID = "apify/facebook-ads-scraper"
ACTOR_WEBSITE_ID = "apify/website-content-crawler"
ACTOR_GOOGLE_SEARCH_ID = "apify/google-search-scraper"
ACTOR_INSTAGRAM_ID = "apify/instagram-scraper"
ACTOR_TIKTOK_ID = "clockworks/tiktok-scraper"
ACTOR_GOOGLE_PLACES_ID = "compass/crawler-google-places"


# ── Per-actor input builders ──────────────────────────────────────────────────

def build_facebook_ads_input(brand_name: str) -> dict[str, Any]:
    """Meta Ad Library — search by page name / brand keyword.

    ``activeStatus`` enum is ``"" | "active" | "inactive"`` — empty string means
    "all statuses" (the actor rejects ``"all"``).
    """
    from urllib.parse import quote_plus
    query = quote_plus(brand_name.strip())
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
        "resultsLimit": 50,
        "activeStatus": "",
    }


def build_google_search_input(brand_name: str) -> dict[str, Any]:
    """Top organic SERP for the brand name."""
    return {
        "queries": brand_name,
        "resultsPerPage": 10,
        "maxPagesPerQuery": 1,
        "countryCode": "us",
        "languageCode": "en",
        "mobileResults": False,
    }


def build_website_input(start_url: str) -> dict[str, Any]:
    """Crawl the competitor's site (capped to 20 pages, text only)."""
    return {
        "startUrls": [{"url": start_url}],
        "crawlerType": "cheerio",
        "maxCrawlPages": 20,
        "maxCrawlDepth": 2,
        "saveMarkdown": True,
        "saveHtml": False,
        "removeCookieWarnings": True,
        "expandIframes": False,
    }


def build_instagram_input(brand_name: str) -> dict[str, Any]:
    """Instagram — search profiles by brand name + pull recent posts from top match."""
    return {
        "search": brand_name,
        "searchType": "user",
        "searchLimit": 5,
        "resultsType": "details",
        "resultsLimit": 30,
        "addParentData": False,
    }


def build_tiktok_input(brand_name: str) -> dict[str, Any]:
    """TikTok — search by keyword across users + recent videos."""
    return {
        "searchQueries": [brand_name],
        "resultsPerPage": 30,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
        "proxyCountryCode": "None",
    }


def build_google_places_input(brand_name: str) -> dict[str, Any]:
    """Google Maps — find places matching the brand name with reviews."""
    return {
        "searchStringsArray": [brand_name],
        "maxCrawledPlacesPerSearch": 10,
        "language": "en",
        "skipClosedPlaces": False,
        "scrapePlaceDetailPage": True,
        "includeWebResults": False,
        "maxReviews": 20,
    }
