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


def test_find_local_elections_uses_client_and_parses_result():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_response(VALID_RESPONSE)

    result = find_local_elections("62704", client=fake_client)

    assert result.zipcode == "62704"
    assert len(result.races) == 2
    called_kwargs = fake_client.messages.create.call_args.kwargs
    assert called_kwargs["model"] == "claude-opus-4-8"
    assert any(t.get("type") == "web_search_20260209" for t in called_kwargs["tools"])
    assert "62704" in called_kwargs["messages"][0]["content"]


def test_find_local_elections_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        find_local_elections("62704")


def test_find_local_elections_raises_on_refusal():
    fake_client = MagicMock()
    refusal_response = MagicMock()
    refusal_response.content = []
    refusal_response.stop_reason = "refusal"
    fake_client.messages.create.return_value = refusal_response

    with pytest.raises(RuntimeError, match="refus"):
        find_local_elections("62704", client=fake_client)
