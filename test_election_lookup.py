import pytest
from election_lookup import parse_lookup_response, LookupResult


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
