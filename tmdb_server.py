"""TMDB MCP server for the Movie Night Planner capstone.

Exposes three FastMCP tools:
- discover_movies(genre, max_runtime, age_rating)
- search_movies(query)
- get_movie_details(movie_id)

All credentials are loaded from .env via TMDB_API_KEY.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

mcp = FastMCP("tmdb-movie-tools")

# Small hardcoded map from TMDB /genre/movie/list.
GENRE_IDS = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "science fiction": 878,
    "sci-fi": 878,
    "tv movie": 10770,
    "thriller": 53,
    "war": 10752,
    "western": 37,
}

# Ordered from youngest-friendly to adult-only for simple filtering.
US_RATING_ORDER = {
    "G": 0,
    "PG": 1,
    "PG-13": 2,
    "R": 3,
    "NC-17": 4,
}


def _require_key() -> str:
    if not TMDB_API_KEY:
        raise RuntimeError("Missing TMDB_API_KEY. Add it to your .env file.")
    return TMDB_API_KEY


def _tmdb_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = dict(params or {})
    params["api_key"] = _require_key()
    with httpx.Client(timeout=15) as client:
        response = client.get(f"{TMDB_BASE_URL}{path}", params=params)
        response.raise_for_status()
        return response.json()


def _year(release_date: str | None) -> str | None:
    if not release_date:
        return None
    try:
        return str(datetime.fromisoformat(release_date).year)
    except ValueError:
        return release_date[:4]


def _certification_from_details(details: dict[str, Any]) -> str | None:
    release_dates = details.get("release_dates", {}).get("results", [])
    us_entry = next((entry for entry in release_dates if entry.get("iso_3166_1") == "US"), None)
    if not us_entry:
        return None

    certifications = [
        rd.get("certification")
        for rd in us_entry.get("release_dates", [])
        if rd.get("certification")
    ]
    return certifications[0] if certifications else None


def _trim_search_result(movie: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": movie.get("id"),
        "title": movie.get("title"),
        "year": _year(movie.get("release_date")),
        "score": movie.get("vote_average"),
    }


def _trim_details(details: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": details.get("id"),
        "title": details.get("title"),
        "year": _year(details.get("release_date")),
        "runtime": details.get("runtime"),
        "certification": _certification_from_details(details),
        "genres": [genre.get("name") for genre in details.get("genres", []) if genre.get("name")],
        "score": details.get("vote_average"),
    }


def _rating_lte(age_rating: str | None) -> str | None:
    """Convert an allowed rating to TMDB certification.lte when possible."""
    if not age_rating:
        return None
    normalized = age_rating.strip().upper()
    return normalized if normalized in US_RATING_ORDER else None


@mcp.tool()
def discover_movies(genre: str, max_runtime: int, age_rating: str = "PG") -> list[dict[str, Any]]:
    """Find TMDB movie candidates by plain-language genre, max runtime, and US age rating.

    Use this for requests like "find us something funny under 2 hours". The genre
    can be a plain name like animation, adventure, comedy, family, sci-fi, etc.
    This returns candidate ids, titles, years, and scores only; call
    get_movie_details for runtime, certification, and genres.
    """
    genre_key = genre.strip().lower()
    genre_id = GENRE_IDS.get(genre_key)
    if genre_id is None:
        return [{"error": f"Unknown genre '{genre}'. Try one of: {', '.join(sorted(GENRE_IDS))}."}]

    params: dict[str, Any] = {
        "with_genres": genre_id,
        "with_runtime.lte": max_runtime,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 100,
        "include_adult": "false",
        "page": 1,
    }
    cert_lte = _rating_lte(age_rating)
    if cert_lte:
        params["certification_country"] = "US"
        params["certification.lte"] = cert_lte

    data = _tmdb_get("/discover/movie", params)
    return [_trim_search_result(movie) for movie in data.get("results", [])[:8]]


@mcp.tool()
def search_movies(query: str) -> list[dict[str, Any]]:
    """Search TMDB movies by title or title-like request.

    Use this when the user names a movie or asks for "something like Jumanji".
    This returns candidate ids, titles, years, and scores only; call
    get_movie_details for runtime, certification, and genres.
    """
    data = _tmdb_get("/search/movie", {"query": query, "include_adult": "false", "page": 1})
    return [_trim_search_result(movie) for movie in data.get("results", [])[:8]]


@mcp.tool()
def get_movie_details(movie_id: int) -> dict[str, Any]:
    """Return clean details for one TMDB movie: title, year, runtime, US certification, genres, and score."""
    details = _tmdb_get(f"/movie/{movie_id}", {"append_to_response": "release_dates"})
    return _trim_details(details)


if __name__ == "__main__":
    mcp.run()
