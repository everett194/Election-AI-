from unittest.mock import MagicMock, patch

import pytest
from election_lookup import (
    Candidate,
    CandidateIssuePosition,
    CandidateIssueProfile,
    LookupResult,
    Position,
    find_local_elections,
    find_local_elections_via_tavily,
    parse_candidate_research_response,
    parse_candidates_evidence_response,
    parse_candidates_prediction_response,
    parse_candidates_research_response,
    parse_lookup_response,
    predict_candidates_for_race,
    research_candidate_positions,
    research_candidates_for_race,
    research_candidates_for_race_with_fallback,
    research_candidates_via_tavily,
)
from tavily_search import SearchResult
from questionnaire_scoring import QUESTIONS


VALID_RESPONSE = """
{
  "races": [
    {
      "office": "mayor",
      "jurisdiction_name": "Springfield",
      "election_date": "2026-11-03",
      "election_type": "general",
      "notes": null,
      "candidates": [
        {
          "name": "Jane Doe",
          "party": "Independent",
          "incumbent": true,
          "positions": [
            {
              "summary": "Supports expanding the downtown bus line.",
              "confidence": "high",
              "sources": [{"url": "https://janedoe.example/platform", "title": "Jane Doe for Mayor"}]
            }
          ]
        }
      ]
    },
    {
      "office": "county",
      "jurisdiction_name": "Example County",
      "election_date": null,
      "election_type": null,
      "notes": "No upcoming county race found for this jurisdiction.",
      "candidates": []
    }
  ]
}
"""


CANDIDATE_RESEARCH_JSON = """
{
  "positions": [
    {
      "question_id": "housing_zoning_density",
      "position": 4,
      "confidence": "high",
      "source": {"url": "https://example.com/vote411", "title": "Vote411 candidate guide"}
    },
    {
      "question_id": "taxes_shortfall",
      "position": 2,
      "confidence": "medium",
      "source": {"url": "https://example.com/news", "title": null}
    }
  ]
}
"""


def test_parses_valid_response():
    result = parse_lookup_response("62704", VALID_RESPONSE)
    assert isinstance(result, LookupResult)
    assert result.zipcode == "62704"
    assert len(result.races) == 2
    assert result.races[0].office == "mayor"
    assert result.races[0].candidates[0].name == "Jane Doe"
    assert result.races[0].candidates[0].positions[0].confidence == "high"
    assert result.races[0].candidates[0].positions[0].sources[0].url == "https://janedoe.example/platform"
    assert result.races[1].candidates == []
    assert result.races[1].notes == "No upcoming county race found for this jurisdiction."


def test_strips_markdown_code_fence():
    fenced = "```json\n" + VALID_RESPONSE + "\n```"
    result = parse_lookup_response("62704", fenced)
    assert len(result.races) == 2


def test_raises_on_malformed_json():
    with pytest.raises(ValueError):
        parse_lookup_response("62704", "not json at all")


def test_raises_on_missing_races_key():
    with pytest.raises(ValueError):
        parse_lookup_response("62704", "{}")


def test_parses_candidate_research_response():
    profile = parse_candidate_research_response("Jane Doe", "mayor", CANDIDATE_RESEARCH_JSON)
    assert profile.candidate_name == "Jane Doe"
    assert profile.office == "mayor"
    assert profile.positions == {"housing_zoning_density": 4, "taxes_shortfall": 2}
    assert len(profile.sourced_positions) == 2
    assert profile.sourced_positions[0].question_id == "housing_zoning_density"
    assert profile.sourced_positions[0].position == 4
    assert profile.sourced_positions[0].confidence == "high"
    assert profile.sourced_positions[0].source.url == "https://example.com/vote411"
    assert profile.sourced_positions[0].source.title == "Vote411 candidate guide"
    assert profile.sourced_positions[1].source.title is None


def test_parses_candidate_research_response_with_zero_coverage():
    profile = parse_candidate_research_response("Jane Doe", "mayor", '{"positions": []}')
    assert profile.positions == {}
    assert profile.sourced_positions == []


def test_candidate_research_response_raises_on_malformed_json():
    with pytest.raises(ValueError):
        parse_candidate_research_response("Jane Doe", "mayor", "not json at all")


def test_candidate_research_response_raises_on_missing_positions_key():
    with pytest.raises(ValueError):
        parse_candidate_research_response("Jane Doe", "mayor", "{}")


def test_candidate_research_response_ignores_unknown_question_ids():
    raw = (
        '{"positions": [{"question_id": "not_a_real_question", "position": 3, '
        '"confidence": "low", "source": {"url": "https://example.com"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}
    assert profile.sourced_positions == []


def test_candidate_research_response_skips_entry_with_out_of_range_position():
    raw = (
        '{"positions": [{"question_id": "housing_zoning_density", "position": 9, '
        '"confidence": "high", "source": {"url": "https://example.com"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}
    assert profile.sourced_positions == []


def test_candidate_research_response_skips_entry_with_non_integer_position():
    raw = (
        '{"positions": [{"question_id": "housing_zoning_density", "position": "4", '
        '"confidence": "high", "source": {"url": "https://example.com"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}


def test_candidate_research_response_skips_entry_with_invalid_confidence():
    raw = (
        '{"positions": [{"question_id": "housing_zoning_density", "position": 4, '
        '"confidence": "very high", "source": {"url": "https://example.com"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}


def test_candidate_research_response_skips_entry_with_missing_source_url():
    raw = (
        '{"positions": [{"question_id": "housing_zoning_density", "position": 4, '
        '"confidence": "high", "source": {"title": "no url here"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}


def test_candidate_research_response_keeps_valid_entries_alongside_invalid_ones():
    raw = (
        '{"positions": ['
        '{"question_id": "housing_zoning_density", "position": 4, "confidence": "high", '
        '"source": {"url": "https://example.com/valid"}},'
        '{"question_id": "taxes_shortfall", "position": 9, "confidence": "high", '
        '"source": {"url": "https://example.com/invalid"}}'
        ']}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {"housing_zoning_density": 4}


def test_candidate_research_response_skips_non_dict_entry_and_keeps_valid_ones():
    raw = (
        '{"positions": ['
        'null, "not a dict", ["also", "not", "a", "dict"], '
        '{"question_id": "housing_zoning_density", "position": 4, "confidence": "high", '
        '"source": {"url": "https://example.com/valid"}}'
        ']}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {"housing_zoning_density": 4}


def test_candidate_research_response_skips_duplicate_question_id():
    raw = (
        '{"positions": ['
        '{"question_id": "housing_zoning_density", "position": 4, "confidence": "high", '
        '"source": {"url": "https://example.com/first"}},'
        '{"question_id": "housing_zoning_density", "position": 1, "confidence": "low", '
        '"source": {"url": "https://example.com/second"}}'
        ']}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {"housing_zoning_density": 4}
    assert len(profile.sourced_positions) == 1


def test_candidate_research_response_rejects_boolean_position():
    raw = (
        '{"positions": [{"question_id": "housing_zoning_density", "position": true, '
        '"confidence": "high", "source": {"url": "https://example.com"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}


def test_candidate_research_response_rejects_non_http_url():
    raw = (
        '{"positions": [{"question_id": "housing_zoning_density", "position": 4, '
        '"confidence": "high", "source": {"url": "javascript:alert(1)"}}]}'
    )
    profile = parse_candidate_research_response("Jane Doe", "mayor", raw)
    assert profile.positions == {}


def test_candidate_research_response_raises_on_non_dict_top_level():
    with pytest.raises(ValueError):
        parse_candidate_research_response("Jane Doe", "mayor", '"positions"')


def test_candidate_issue_profile_covered_categories():
    profile = CandidateIssueProfile(
        candidate_name="Jane Doe",
        office="mayor",
        positions={"housing_zoning_density": 4, "safety_police_funding": 2},
    )
    assert profile.covered_categories() == {"housing", "safety"}


def test_candidate_issue_profile_covered_axes_both_covered():
    # housing_zoning_density has econ_weight=2, social_weight=0
    # safety_police_funding has econ_weight=0, social_weight=2
    profile = CandidateIssueProfile(
        candidate_name="Jane Doe",
        office="mayor",
        positions={"housing_zoning_density": 4, "safety_police_funding": 2},
    )
    assert profile.covered_axes() == (True, True)


def test_candidate_issue_profile_covered_axes_only_econ():
    profile = CandidateIssueProfile(
        candidate_name="Jane Doe",
        office="mayor",
        positions={"housing_zoning_density": 4},
    )
    assert profile.covered_axes() == (True, False)


def test_candidate_issue_profile_covered_axes_none_covered():
    profile = CandidateIssueProfile(candidate_name="Jane Doe", office="mayor", positions={})
    assert profile.covered_axes() == (False, False)


def _mock_response(text: str):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"
    return response


def _valid_single_race_json(office: str) -> str:
    jurisdiction = {
        "mayor": "Springfield",
        "county": "Example County",
        "us_house": "Example District",
    }[office]
    return f"""{{
      "races": [
        {{
          "office": "{office}",
          "jurisdiction_name": "{jurisdiction}",
          "election_date": "2026-11-03",
          "election_type": "general",
          "notes": null,
          "candidates": []
        }}
      ]
    }}"""


def _office_from_prompt(content: str) -> str:
    if "mayoral election" in content:
        return "mayor"
    if "county-level election" in content:
        return "county"
    if "U.S. House" in content:
        return "us_house"
    raise AssertionError(f"unrecognized prompt: {content[:80]!r}")


def test_find_local_elections_makes_three_scoped_calls():
    fake_client = MagicMock()

    def side_effect(*args, **kwargs):
        office = _office_from_prompt(kwargs["messages"][0]["content"])
        return _mock_response(_valid_single_race_json(office))

    fake_client.messages.create.side_effect = side_effect

    result = find_local_elections("62704", client=fake_client)

    assert fake_client.messages.create.call_count == 3
    assert [r.office for r in result.races] == ["mayor", "county", "us_house"]
    assert result.races[0].jurisdiction_name == "Springfield"

    for call in fake_client.messages.create.call_args_list:
        assert call.kwargs["output_config"] == {"effort": "low"}
        assert call.kwargs["tools"][0]["max_uses"] == 5


def test_find_local_elections_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        find_local_elections("62704")


def test_find_local_elections_degrades_gracefully_on_single_office_failure():
    fake_client = MagicMock()

    def side_effect(*args, **kwargs):
        office = _office_from_prompt(kwargs["messages"][0]["content"])
        if office == "county":
            refusal_response = MagicMock()
            refusal_response.content = []
            refusal_response.stop_reason = "refusal"
            return refusal_response
        return _mock_response(_valid_single_race_json(office))

    fake_client.messages.create.side_effect = side_effect

    result = find_local_elections("62704", client=fake_client)

    by_office = {r.office: r for r in result.races}
    assert by_office["mayor"].jurisdiction_name == "Springfield"
    assert by_office["us_house"].jurisdiction_name == "Example District"
    assert by_office["county"].candidates == []
    assert "failed" in by_office["county"].notes.lower()


COMBINED_RACES_EVIDENCE_JSON = """{
  "races": [
    {
      "office": "mayor",
      "jurisdiction_name": "Springfield",
      "election_date": "2026-11-03",
      "election_type": "general",
      "notes": null,
      "candidates": [
        {
          "name": "Jane Doe",
          "party": "Independent",
          "incumbent": true,
          "positions": [
            {"summary": "Supports expanding the downtown bus line.", "confidence": "high",
             "sources": [{"url": "https://example.com/jane", "title": "Platform"}]}
          ]
        }
      ]
    },
    {
      "office": "county",
      "jurisdiction_name": "Unknown",
      "election_date": null,
      "election_type": null,
      "notes": "No evidence found for a county race.",
      "candidates": []
    },
    {
      "office": "us_house",
      "jurisdiction_name": "Example District",
      "election_date": "2026-11-03",
      "election_type": "general",
      "notes": null,
      "candidates": []
    }
  ]
}"""


def test_find_local_elections_via_tavily_fetches_evidence_then_synthesizes():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response(COMBINED_RACES_EVIDENCE_JSON)

    def fake_search_many(queries, max_results_per_query=5, api_key=None, search_depth='basic'):
        return {
            query: [SearchResult(title="Result", url="https://example.com/x", content="Some evidence text")]
            for query in queries
        }

    with patch("election_lookup.tavily_search.search_many", side_effect=fake_search_many) as mock_search_many, \
         patch("election_lookup._resolve_zipcode_place", return_value=None):
        result = find_local_elections_via_tavily("62704", client=fake_client)

    # One Tavily fan-out call covering all three race types at once.
    assert mock_search_many.call_count == 1
    searched_queries = mock_search_many.call_args.args[0]
    assert any("mayor" in q for q in searched_queries)
    assert any("county" in q for q in searched_queries)
    assert any("US House" in q for q in searched_queries)

    # Exactly one Claude call for all three races, without the web_search tool
    # (evidence was pre-fetched, so Claude doesn't need to search itself).
    assert fake_client.messages.create.call_count == 1
    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs

    assert [r.office for r in result.races] == ["mayor", "county", "us_house"]
    assert result.races[0].jurisdiction_name == "Springfield"
    assert result.races[0].candidates[0].name == "Jane Doe"
    assert result.races[1].candidates == []


def test_find_local_elections_via_tavily_runs_broad_query_set_at_basic_depth():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response(COMBINED_RACES_EVIDENCE_JSON)

    def fake_search_many(queries, max_results_per_query=5, api_key=None, search_depth='basic'):
        return {
            query: [SearchResult(title="Result", url="https://example.com/x", content="Some evidence text")]
            for query in queries
        }

    with patch("election_lookup.tavily_search.search_many", side_effect=fake_search_many) as mock_search_many, \
         patch("election_lookup._resolve_zipcode_place", return_value=None):
        find_local_elections_via_tavily("62704", client=fake_client)
        query_count = len(mock_search_many.call_args.args[0])
        kwargs = mock_search_many.call_args.kwargs

    # 11 queries per office (mayor, county, us_house), all at Tavily's fast
    # "basic" depth -- breadth of queries, not per-query depth, is what
    # finds a complete candidate list quickly.
    assert query_count == 33
    assert kwargs.get("search_depth") == "basic"


def test_find_local_elections_via_tavily_drops_placeholder_candidate_names():
    fake_client = MagicMock()
    races_with_placeholder = """{
      "races": [
        {
          "office": "mayor",
          "jurisdiction_name": "Springfield",
          "election_date": null,
          "election_type": null,
          "notes": null,
          "candidates": [
            {"name": "Jane Doe", "party": "Independent", "incumbent": true, "positions": []},
            {"name": "Kent County Commissioner candidates (unidentified)", "party": null,
             "incumbent": null, "positions": []}
          ]
        },
        {"office": "county", "jurisdiction_name": "Unknown", "election_date": null,
         "election_type": null, "notes": "none", "candidates": []},
        {"office": "us_house", "jurisdiction_name": "Unknown", "election_date": null,
         "election_type": null, "notes": "none", "candidates": []}
      ]
    }"""
    fake_client.messages.create.return_value = _mock_response(races_with_placeholder)

    with patch("election_lookup.tavily_search.search_many", return_value={}), \
         patch("election_lookup._resolve_zipcode_place", return_value=None):
        result = find_local_elections_via_tavily("62704", client=fake_client)

    mayor = next(r for r in result.races if r.office == "mayor")
    assert [c.name for c in mayor.candidates] == ["Jane Doe"]


def test_find_local_elections_via_tavily_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("election_lookup.tavily_search.search_many", return_value={}), \
         patch("election_lookup._resolve_zipcode_place", return_value=None):
        with pytest.raises(RuntimeError):
            find_local_elections_via_tavily("62704")


def test_find_local_elections_via_tavily_raises_when_no_races_returned():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response('{"races": []}')

    with patch("election_lookup.tavily_search.search_many", return_value={}), \
         patch("election_lookup._resolve_zipcode_place", return_value=None):
        with pytest.raises(ValueError):
            find_local_elections_via_tavily("62704", client=fake_client)


def test_research_candidate_positions_calls_api_with_all_questions_and_context():
    fake_client = MagicMock()
    captured = {}

    def side_effect(*args, **kwargs):
        captured["kwargs"] = kwargs
        return _mock_response(CANDIDATE_RESEARCH_JSON)

    fake_client.messages.create.side_effect = side_effect

    candidate = Candidate(
        name="Jane Doe",
        party="Independent",
        incumbent=True,
        positions=[
            Position(
                summary="Supports expanding the downtown bus line.",
                confidence="high",
                sources=[],
            )
        ],
    )

    profile = research_candidate_positions(
        "62704", "mayor", "Springfield", candidate, client=fake_client
    )

    assert profile.candidate_name == "Jane Doe"
    assert profile.office == "mayor"
    assert profile.positions == {"housing_zoning_density": 4, "taxes_shortfall": 2}

    prompt = captured["kwargs"]["messages"][0]["content"]
    assert "Jane Doe" in prompt
    assert "Independent" in prompt
    assert "incumbent" in prompt.lower()
    assert "Springfield" in prompt
    assert "Supports expanding the downtown bus line." in prompt
    for question in QUESTIONS:
        assert question.id in prompt

    assert captured["kwargs"]["model"] == "claude-sonnet-5"
    assert captured["kwargs"]["output_config"] == {"effort": "low"}
    assert captured["kwargs"]["tools"][0]["max_uses"] == 5


def test_research_candidate_positions_includes_zipcode_in_prompt():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response('{"positions": []}')
    candidate = Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])
    research_candidate_positions("62704", "mayor", "Springfield", candidate, client=fake_client)
    prompt = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "62704" in prompt


def test_research_candidate_positions_omits_context_for_candidate_with_no_known_info():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response('{"positions": []}')

    candidate = Candidate(name="Pat Lee", party=None, incumbent=None, positions=[])
    research_candidate_positions("62704", "us_house", "Example District", candidate, client=fake_client)

    prompt = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Pat Lee" in prompt
    assert "Example District" in prompt
    assert "(incumbent)" not in prompt
    assert "Positions already documented for this candidate" not in prompt


def test_research_candidate_positions_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    candidate = Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])
    with pytest.raises(RuntimeError):
        research_candidate_positions("62704", "mayor", "Springfield", candidate)


def test_research_candidate_positions_raises_on_refusal():
    fake_client = MagicMock()
    refusal_response = MagicMock()
    refusal_response.content = []
    refusal_response.stop_reason = "refusal"
    fake_client.messages.create.return_value = refusal_response

    candidate = Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])
    with pytest.raises(RuntimeError):
        research_candidate_positions("62704", "mayor", "Springfield", candidate, client=fake_client)


CANDIDATES_BATCH_JSON = """
{
  "candidates": [
    {
      "name": "Jane Doe",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 4, "confidence": "high",
         "source": {"url": "https://example.com/jane-vote411", "title": "Vote411 guide"}}
      ]
    },
    {
      "name": "John Smith",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 1, "confidence": "medium",
         "source": {"url": "https://example.com/john-news", "title": null}},
        {"question_id": "taxes_shortfall", "position": 5, "confidence": "high",
         "source": {"url": "https://example.com/john-vote411", "title": "Vote411 guide"}}
      ]
    }
  ]
}
"""


def test_parses_candidates_research_response():
    profiles = parse_candidates_research_response(
        "mayor", ["Jane Doe", "John Smith"], CANDIDATES_BATCH_JSON
    )
    assert set(profiles.keys()) == {"Jane Doe", "John Smith"}
    assert profiles["Jane Doe"].positions == {"housing_zoning_density": 4}
    assert profiles["John Smith"].positions == {
        "housing_zoning_density": 1,
        "taxes_shortfall": 5,
    }
    assert profiles["Jane Doe"].office == "mayor"
    assert len(profiles["John Smith"].sourced_positions) == 2


def test_candidates_research_response_skips_unknown_candidate_name():
    raw = (
        '{"candidates": [{"name": "Someone Else", "positions": '
        '[{"question_id": "housing_zoning_density", "position": 4, "confidence": "high", '
        '"source": {"url": "https://example.com"}}]}]}'
    )
    profiles = parse_candidates_research_response("mayor", ["Jane Doe"], raw)
    assert profiles == {}


def test_candidates_research_response_skips_duplicate_candidate_name():
    raw = (
        '{"candidates": ['
        '{"name": "Jane Doe", "positions": [{"question_id": "housing_zoning_density", '
        '"position": 4, "confidence": "high", "source": {"url": "https://example.com/first"}}]},'
        '{"name": "Jane Doe", "positions": [{"question_id": "taxes_shortfall", '
        '"position": 1, "confidence": "low", "source": {"url": "https://example.com/second"}}]}'
        ']}'
    )
    profiles = parse_candidates_research_response("mayor", ["Jane Doe"], raw)
    assert profiles["Jane Doe"].positions == {"housing_zoning_density": 4}


def test_candidates_research_response_raises_on_missing_candidates_key():
    with pytest.raises(ValueError):
        parse_candidates_research_response("mayor", ["Jane Doe"], "{}")


def test_candidates_research_response_handles_empty_candidate_list():
    profiles = parse_candidates_research_response("mayor", [], '{"candidates": []}')
    assert profiles == {}


def test_research_candidates_for_race_returns_empty_dict_for_no_candidates():
    fake_client = MagicMock()
    result = research_candidates_for_race("62704", "mayor", "Springfield", [], client=fake_client)
    assert result == {}
    fake_client.messages.create.assert_not_called()


def test_research_candidates_for_race_makes_one_call_for_all_candidates():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response(CANDIDATES_BATCH_JSON)

    candidates = [
        Candidate(name="Jane Doe", party="Independent", incumbent=True, positions=[]),
        Candidate(name="John Smith", party="Democratic", incumbent=False, positions=[]),
    ]
    profiles = research_candidates_for_race("62704", "mayor", "Springfield", candidates, client=fake_client)

    assert fake_client.messages.create.call_count == 1
    assert set(profiles.keys()) == {"Jane Doe", "John Smith"}

    prompt = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Jane Doe" in prompt
    assert "John Smith" in prompt
    assert "Independent" in prompt
    assert "incumbent" in prompt.lower()
    assert "Springfield" in prompt
    assert "62704" in prompt
    for question in QUESTIONS:
        assert question.id in prompt


def test_research_candidates_for_race_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    candidates = [Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])]
    with pytest.raises(RuntimeError):
        research_candidates_for_race("62704", "mayor", "Springfield", candidates)


CANDIDATES_PREDICTION_JSON = """
{
  "candidates": [
    {
      "name": "Jane Doe",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 4},
        {"question_id": "taxes_shortfall", "position": 2}
      ]
    },
    {
      "name": "John Smith",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 1}
      ]
    }
  ]
}
"""


def test_parses_candidates_prediction_response():
    profiles = parse_candidates_prediction_response(
        "mayor", ["Jane Doe", "John Smith"], CANDIDATES_PREDICTION_JSON
    )
    assert set(profiles.keys()) == {"Jane Doe", "John Smith"}
    assert profiles["Jane Doe"].positions == {"housing_zoning_density": 4, "taxes_shortfall": 2}
    assert profiles["Jane Doe"].sourced_positions == []
    assert profiles["John Smith"].positions == {"housing_zoning_density": 1}
    assert profiles["Jane Doe"].office == "mayor"


def test_candidates_prediction_response_skips_unknown_candidate_name():
    raw = '{"candidates": [{"name": "Someone Else", "positions": [{"question_id": "housing_zoning_density", "position": 4}]}]}'
    profiles = parse_candidates_prediction_response("mayor", ["Jane Doe"], raw)
    assert profiles == {}


def test_candidates_prediction_response_rejects_out_of_range_position():
    raw = '{"candidates": [{"name": "Jane Doe", "positions": [{"question_id": "housing_zoning_density", "position": 9}]}]}'
    profiles = parse_candidates_prediction_response("mayor", ["Jane Doe"], raw)
    assert profiles["Jane Doe"].positions == {}


def test_candidates_prediction_response_raises_on_missing_candidates_key():
    with pytest.raises(ValueError):
        parse_candidates_prediction_response("mayor", ["Jane Doe"], "{}")


def test_predict_candidates_for_race_returns_empty_dict_for_no_candidates():
    fake_client = MagicMock()
    result = predict_candidates_for_race("62704", "mayor", "Springfield", [], client=fake_client)
    assert result == {}
    fake_client.messages.create.assert_not_called()


def test_predict_candidates_for_race_skips_web_search_tool():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response(CANDIDATES_PREDICTION_JSON)

    candidates = [
        Candidate(name="Jane Doe", party="Independent", incumbent=True, positions=[]),
        Candidate(name="John Smith", party="Democratic", incumbent=False, positions=[]),
    ]
    profiles = predict_candidates_for_race("62704", "mayor", "Springfield", candidates, client=fake_client)

    assert fake_client.messages.create.call_count == 1
    assert set(profiles.keys()) == {"Jane Doe", "John Smith"}

    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs

    prompt = call_kwargs["messages"][0]["content"]
    assert "Jane Doe" in prompt
    assert "John Smith" in prompt
    assert "Do not use any tools or search the web" in prompt
    for question in QUESTIONS:
        assert question.id in prompt


def test_predict_candidates_for_race_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    candidates = [Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])]
    with pytest.raises(RuntimeError):
        predict_candidates_for_race("62704", "mayor", "Springfield", candidates)


CANDIDATES_EVIDENCE_JSON = """
{
  "candidates": [
    {
      "name": "Jane Doe",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 4,
         "confidence": "explicit", "source_url": "https://example.com/jane-vote411"},
        {"question_id": "taxes_shortfall", "position": 2,
         "confidence": "weak_inference", "source_url": "https://example.com/jane-news"}
      ]
    },
    {
      "name": "John Smith",
      "positions": [
        {"question_id": "housing_zoning_density", "position": 1,
         "confidence": "strong_inference", "source_url": "https://example.com/john-record"}
      ]
    }
  ]
}
"""


def test_parses_candidates_evidence_response():
    profiles = parse_candidates_evidence_response(
        "mayor", ["Jane Doe", "John Smith"], CANDIDATES_EVIDENCE_JSON
    )
    assert set(profiles.keys()) == {"Jane Doe", "John Smith"}
    assert profiles["Jane Doe"].positions == {"housing_zoning_density": 4, "taxes_shortfall": 2}
    assert profiles["Jane Doe"].sourced_positions[0].confidence == "explicit"
    assert profiles["Jane Doe"].sourced_positions[0].source.url == "https://example.com/jane-vote411"
    assert profiles["John Smith"].sourced_positions[0].confidence == "strong_inference"


def test_candidates_evidence_response_rejects_old_confidence_taxonomy():
    # "high"/"medium"/"low" (the old race-search taxonomy) must not be
    # silently accepted here -- only the explicit/strong_inference/
    # weak_inference taxonomy is valid for evidence-based answers.
    raw = (
        '{"candidates": [{"name": "Jane Doe", "positions": '
        '[{"question_id": "housing_zoning_density", "position": 4, '
        '"confidence": "high", "source_url": "https://example.com"}]}]}'
    )
    profiles = parse_candidates_evidence_response("mayor", ["Jane Doe"], raw)
    assert profiles["Jane Doe"].positions == {}


def test_candidates_evidence_response_rejects_non_http_source_url():
    raw = (
        '{"candidates": [{"name": "Jane Doe", "positions": '
        '[{"question_id": "housing_zoning_density", "position": 4, '
        '"confidence": "explicit", "source_url": "javascript:alert(1)"}]}]}'
    )
    profiles = parse_candidates_evidence_response("mayor", ["Jane Doe"], raw)
    assert profiles["Jane Doe"].positions == {}


def test_candidates_evidence_response_raises_on_missing_candidates_key():
    with pytest.raises(ValueError):
        parse_candidates_evidence_response("mayor", ["Jane Doe"], "{}")


def test_research_candidates_via_tavily_returns_empty_dict_for_no_candidates():
    fake_client = MagicMock()
    result = research_candidates_via_tavily("62704", "mayor", "Springfield", [], client=fake_client)
    assert result == {}
    fake_client.messages.create.assert_not_called()


def test_research_candidates_via_tavily_fetches_evidence_then_synthesizes():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response(CANDIDATES_EVIDENCE_JSON)

    candidates = [
        Candidate(name="Jane Doe", party="Independent", incumbent=True, positions=[]),
        Candidate(name="John Smith", party="Democratic", incumbent=False, positions=[]),
    ]

    def fake_search_many(queries, max_results_per_query=5, api_key=None, search_depth='basic'):
        return {
            query: [SearchResult(title="Result", url="https://example.com/x", content="Some evidence text")]
            for query in queries
        }

    with patch("election_lookup.tavily_search.search_many", side_effect=fake_search_many) as mock_search_many:
        profiles = research_candidates_via_tavily(
            "62704", "mayor", "Springfield", candidates, client=fake_client
        )

    assert set(profiles.keys()) == {"Jane Doe", "John Smith"}

    # One Tavily fan-out call covering every candidate's queries at once.
    assert mock_search_many.call_count == 1
    searched_queries = mock_search_many.call_args.args[0]
    assert any("Jane Doe" in q for q in searched_queries)
    assert any("John Smith" in q for q in searched_queries)

    # Exactly one Claude call (batched per race), without the web_search tool
    # (evidence was pre-fetched, so Claude doesn't need to search itself).
    assert fake_client.messages.create.call_count == 1
    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs

    prompt = call_kwargs["messages"][0]["content"]
    assert "Jane Doe" in prompt
    assert "John Smith" in prompt
    assert "https://example.com/x" in prompt
    assert "explicit" in prompt
    assert "strong_inference" in prompt
    assert "weak_inference" in prompt


def test_research_candidates_via_tavily_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    candidates = [Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])]
    with patch("election_lookup.tavily_search.search_many", return_value={}):
        with pytest.raises(RuntimeError):
            research_candidates_via_tavily("62704", "mayor", "Springfield", candidates)


def _empty_evidence_search_many(queries, max_results_per_query=5, api_key=None, search_depth='basic'):
    return {query: [] for query in queries}


def test_fallback_returns_empty_dict_for_no_candidates():
    fake_client = MagicMock()
    result = research_candidates_for_race_with_fallback(
        "62704", "mayor", "Springfield", [], client=fake_client
    )
    assert result == {}
    fake_client.messages.create.assert_not_called()


def test_fallback_fills_gaps_with_speculation_when_sourced_coverage_is_thin():
    fake_client = MagicMock()

    def fake_create(*args, **kwargs):
        content = kwargs["messages"][0]["content"]
        if "analyzing pre-gathered web search" in content:
            # Real research finds only one sourced position.
            text = (
                '{"candidates": [{"name": "Jane Doe", "positions": '
                '[{"question_id": "housing_zoning_density", "position": 4, '
                '"confidence": "explicit", "source_url": "https://example.com/jane"}]}]}'
            )
        elif "Do not use any tools" in content:
            # Speculative fallback covers more questions, including the one
            # already sourced (which must NOT override the sourced answer).
            text = (
                '{"candidates": [{"name": "Jane Doe", "positions": ['
                '{"question_id": "housing_zoning_density", "position": 1}, '
                '{"question_id": "taxes_shortfall", "position": 3}'
                ']}]}'
            )
        else:
            raise AssertionError(f"unexpected prompt: {content[:80]!r}")
        return _mock_response(text)

    fake_client.messages.create.side_effect = fake_create

    candidates = [Candidate(name="Jane Doe", party="Independent", incumbent=True, positions=[])]

    with patch("election_lookup.tavily_search.search_many", side_effect=_empty_evidence_search_many):
        profiles = research_candidates_for_race_with_fallback(
            "62704", "mayor", "Springfield", candidates, client=fake_client
        )

    profile = profiles["Jane Doe"]
    # Sourced answer wins for the overlapping question.
    assert profile.positions["housing_zoning_density"] == 4
    # Speculative fallback fills the gap.
    assert profile.positions["taxes_shortfall"] == 3

    by_question = {p.question_id: p for p in profile.sourced_positions}
    assert by_question["housing_zoning_density"].confidence == "explicit"
    assert by_question["housing_zoning_density"].source.url == "https://example.com/jane"
    assert by_question["taxes_shortfall"].confidence == "speculative"
    assert by_question["taxes_shortfall"].source is None

    # Two calls total: one evidence-extrapolation call, one speculative call.
    assert fake_client.messages.create.call_count == 2


def test_fallback_skips_speculation_for_a_fully_sourced_candidate():
    fake_client = MagicMock()
    all_questions_json = ",".join(
        f'{{"question_id": "{q.id}", "position": 3, "confidence": "explicit", '
        f'"source_url": "https://example.com/{q.id}"}}'
        for q in QUESTIONS
    )
    evidence_text = f'{{"candidates": [{{"name": "Jane Doe", "positions": [{all_questions_json}]}}]}}'

    def fake_create(*args, **kwargs):
        content = kwargs["messages"][0]["content"]
        if "analyzing pre-gathered web search" in content:
            return _mock_response(evidence_text)
        raise AssertionError("speculation should not be called for a fully-sourced candidate")

    fake_client.messages.create.side_effect = fake_create
    candidates = [Candidate(name="Jane Doe", party=None, incumbent=None, positions=[])]

    with patch("election_lookup.tavily_search.search_many", side_effect=_empty_evidence_search_many):
        profiles = research_candidates_for_race_with_fallback(
            "62704", "mayor", "Springfield", candidates, client=fake_client
        )

    assert len(profiles["Jane Doe"].positions) == len(QUESTIONS)
    assert fake_client.messages.create.call_count == 1
