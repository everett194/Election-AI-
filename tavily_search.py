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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests

TAVILY_API_URL = "https://api.tavily.com/search"

# A single race/candidate search fires 30+ Tavily queries concurrently, so a
# burst that trips Tavily's rate limit is expected occasionally, not
# exceptional -- retry those with backoff instead of failing the whole
# search. Non-429 errors (bad request, auth failure, network blip) are not
# retried; they're either not transient or already handled per-query by
# search_many.
_MAX_429_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1.5


@dataclass
class SearchResult:
    title: str
    url: str
    content: str


def search(
    query: str, max_results: int = 5, api_key: str | None = None, search_depth: str = "basic"
) -> list[SearchResult]:
    """Runs one Tavily search query and returns its results.

    search_depth="advanced" asks Tavily for a more thorough (but slower and
    more expensive) search -- worth it for background/non-blocking research
    where a few extra seconds don't hurt perceived speed, not worth it for
    anything the user is actively waiting on.
    """
    api_key = api_key or os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Set it in your environment before "
            "searching (e.g. `export TAVILY_API_KEY=tvly-...`)."
        )
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
    }
    response = requests.post(TAVILY_API_URL, json=payload, timeout=30)
    attempt = 0
    while response.status_code == 429 and attempt < _MAX_429_RETRIES:
        retry_after = response.headers.get("Retry-After")
        delay = float(retry_after) if retry_after else _BACKOFF_BASE_SECONDS * (2**attempt)
        time.sleep(delay)
        attempt += 1
        response = requests.post(TAVILY_API_URL, json=payload, timeout=30)
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
    queries: list[str],
    max_results_per_query: int = 5,
    api_key: str | None = None,
    search_depth: str = "basic",
) -> dict[str, list[SearchResult]]:
    """Runs every query in `queries` in parallel and returns {query: results}.
    A single query failing (one bad request, a transient network blip) doesn't
    affect the others -- it just yields an empty result list for that query.

    But if EVERY query fails, that's not "nothing found" -- it's a systemic
    problem (missing/invalid TAVILY_API_KEY, Tavily is down, no network), and
    silently returning all-empty results makes that failure indistinguishable
    from a real, legitimate zero-result search. In that case, raise instead.
    """
    if not queries:
        return {}
    results: dict[str, list[SearchResult]] = {}
    errors: dict[str, Exception] = {}
    with ThreadPoolExecutor(max_workers=min(40, len(queries))) as executor:
        future_to_query = {
            executor.submit(search, query, max_results_per_query, api_key, search_depth): query
            for query in queries
        }
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                results[query] = future.result()
            except Exception as exc:
                results[query] = []
                errors[query] = exc
    if errors and len(errors) == len(queries):
        sample = next(iter(errors.values()))
        if "429" in str(sample):
            raise RuntimeError(
                f"Tavily rate limit exceeded even after retrying ({len(queries)} queries). "
                "Wait a bit before searching again, or check your plan's rate limit at "
                f"https://tavily.com. Sample error: {sample}"
            )
        raise RuntimeError(
            f"Tavily search failed for all {len(queries)} queries -- check TAVILY_API_KEY "
            f"and your network connection. Sample error: {sample}"
        )
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
