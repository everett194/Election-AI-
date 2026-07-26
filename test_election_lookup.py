from unittest.mock import MagicMock

import pytest
from election_lookup import (
    Candidate,
    CandidateIssuePosition,
    CandidateIssueProfile,
    LookupResult,
    Position,
    find_local_elections,
    parse_candidate_research_response,
    parse_lookup_response,
    research_candidate_positions,
)
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
