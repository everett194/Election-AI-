from unittest.mock import MagicMock

import pytest
from election_lookup import parse_lookup_response, find_local_elections, LookupResult


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
