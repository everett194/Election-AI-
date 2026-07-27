"""
tavily_search.py

Thin wrapper around the Tavily search API (https://tavily.com). Runs
multiple queries in parallel over plain HTTP -- Tavily is a hosted search
API, not an agentic tool loop, so ordinary thread-based concurrency is safe
and fast here. (This is different from calling the Anthropic API
concurrently, which hit rate limits when tried earlier in this project's
history -- see git history on election_lookup.py. Tavily has no such
constraint for this usage.)

Requires TAVILY_API_KEY in the environment. Get a key at
https://tavily.com and set it yourself -- never pass it in plaintext
through an AI assistant or commit it to the repo.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests

TAVILY_API_URL = "https://api.tavily.com/search"


@dataclass
class SearchResult:
    title: str
    url: str
    content: str


def search(query: str, max_results: int = 5, api_key: str | None = None) -> list[SearchResult]:
    """Runs one Tavily search query and returns its results."""
    api_key = api_key or os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Set it in your environment before "
            "searching (e.g. `export TAVILY_API_KEY=tvly-...`)."
        )
    response = requests.post(
        TAVILY_API_URL,
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return [
        SearchResult(
            title=item.get("title") or "",
            url=item["url"],
            content=item.get("content") or "",
        )
        for item in data.get("results", [])
        if item.get("url")
    ]


def search_many(
    queries: list[str], max_results_per_query: int = 5, api_key: str | None = None
) -> dict[str, list[SearchResult]]:
    """Runs every query in `queries` in parallel and returns {query: results}.
    One query's failure (network error, bad response, etc.) doesn't affect
    the others -- it just yields an empty result list for that query.
    """
    if not queries:
        return {}
    results: dict[str, list[SearchResult]] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(queries))) as executor:
        future_to_query = {
            executor.submit(search, query, max_results_per_query, api_key): query
            for query in queries
        }
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                results[query] = future.result()
            except Exception:
                results[query] = []
    return results


def dedupe_by_url(results: list[SearchResult]) -> list[SearchResult]:
    """Collapses a list of results down to one entry per unique URL,
    preserving first-seen order."""
    seen: set[str] = set()
    deduped: list[SearchResult] = []
    for result in results:
        if result.url in seen:
            continue
        seen.add(result.url)
        deduped.append(result)
    return deduped
