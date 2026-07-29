from unittest.mock import MagicMock, patch

import pytest

from tavily_search import SearchResult, dedupe_by_url, search, search_many


def _mock_post_response(results: list[dict]):
    response = MagicMock()
    response.json.return_value = {"results": results}
    response.raise_for_status.return_value = None
    return response


def test_search_returns_parsed_results():
    fake_results = [
        {"title": "Vote411 guide", "url": "https://example.com/a", "content": "Some text"},
        {"title": "News article", "url": "https://example.com/b", "content": "More text"},
    ]
    with patch("tavily_search.requests.post", return_value=_mock_post_response(fake_results)) as mock_post:
        results = search("Jane Doe housing position", max_results=5, api_key="test-key")

    assert results == [
        SearchResult(title="Vote411 guide", url="https://example.com/a", content="Some text"),
        SearchResult(title="News article", url="https://example.com/b", content="More text"),
    ]
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["query"] == "Jane Doe housing position"
    assert call_kwargs["json"]["api_key"] == "test-key"
    assert call_kwargs["json"]["max_results"] == 5


def test_search_skips_results_with_no_url():
    fake_results = [
        {"title": "No URL here", "content": "text"},
        {"title": "Has URL", "url": "https://example.com/a", "content": "text"},
    ]
    with patch("tavily_search.requests.post", return_value=_mock_post_response(fake_results)):
        results = search("query", api_key="test-key")
    assert len(results) == 1
    assert results[0].url == "https://example.com/a"


def test_search_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        search("some query")


def test_search_many_runs_every_query_and_keys_by_query():
    def fake_search(query, max_results=5, api_key=None, search_depth='basic'):
        return [SearchResult(title=query, url=f"https://example.com/{query}", content="text")]

    with patch("tavily_search.search", side_effect=fake_search):
        results = search_many(["query one", "query two"], api_key="test-key")

    assert set(results.keys()) == {"query one", "query two"}
    assert results["query one"][0].url == "https://example.com/query one"


def test_search_many_isolates_a_failing_query():
    def fake_search(query, max_results=5, api_key=None, search_depth='basic'):
        if query == "bad query":
            raise RuntimeError("network error")
        return [SearchResult(title=query, url="https://example.com/ok", content="text")]

    with patch("tavily_search.search", side_effect=fake_search):
        results = search_many(["good query", "bad query"], api_key="test-key")

    assert results["good query"] != []
    assert results["bad query"] == []


def test_search_many_returns_empty_dict_for_no_queries():
    assert search_many([]) == {}


def test_search_many_raises_when_every_query_fails():
    def fake_search(query, max_results=5, api_key=None, search_depth='basic'):
        raise RuntimeError("401 Unauthorized")

    with patch("tavily_search.search", side_effect=fake_search):
        with pytest.raises(RuntimeError, match="failed for all 2 queries"):
            search_many(["query one", "query two"], api_key="bad-key")


def test_search_many_does_not_raise_when_only_some_queries_fail():
    def fake_search(query, max_results=5, api_key=None, search_depth='basic'):
        if query == "bad query":
            raise RuntimeError("network error")
        return [SearchResult(title=query, url="https://example.com/ok", content="text")]

    with patch("tavily_search.search", side_effect=fake_search):
        results = search_many(["good query", "bad query"], api_key="test-key")

    assert results["good query"] != []
    assert results["bad query"] == []


def test_dedupe_by_url_keeps_first_occurrence():
    results = [
        SearchResult(title="First", url="https://example.com/a", content="1"),
        SearchResult(title="Duplicate", url="https://example.com/a", content="2"),
        SearchResult(title="Second", url="https://example.com/b", content="3"),
    ]
    deduped = dedupe_by_url(results)
    assert len(deduped) == 2
    assert deduped[0].title == "First"
    assert deduped[1].url == "https://example.com/b"
