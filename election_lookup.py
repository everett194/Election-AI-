from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

import anthropic


@dataclass
class Source:
    url: str
    title: str | None = None


@dataclass
class Position:
    summary: str
    confidence: Literal["high", "medium", "low"]
    sources: list[Source] = field(default_factory=list)


@dataclass
class Candidate:
    name: str
    party: str | None
    incumbent: bool | None
    positions: list[Position] = field(default_factory=list)


@dataclass
class Race:
    office: Literal["mayor", "county", "us_house"]
    jurisdiction_name: str
    election_date: str | None
    election_type: Literal["primary", "general"] | None
    candidates: list[Candidate] = field(default_factory=list)
    notes: str | None = None


@dataclass
class LookupResult:
    zipcode: str
    races: list[Race]
    retrieved_at: str


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1) if match else stripped


def parse_lookup_response(zipcode: str, raw_text: str) -> LookupResult:
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if "races" not in data or not isinstance(data["races"], list):
        raise ValueError("Model response JSON is missing a 'races' array")

    races = []
    for race_data in data["races"]:
        candidates = []
        for cand_data in race_data.get("candidates", []):
            positions = []
            for pos_data in cand_data.get("positions", []):
                sources = [
                    Source(url=s["url"], title=s.get("title"))
                    for s in pos_data.get("sources", [])
                ]
                positions.append(
                    Position(
                        summary=pos_data["summary"],
                        confidence=pos_data["confidence"],
                        sources=sources,
                    )
                )
            candidates.append(
                Candidate(
                    name=cand_data["name"],
                    party=cand_data.get("party"),
                    incumbent=cand_data.get("incumbent"),
                    positions=positions,
                )
            )
        races.append(
            Race(
                office=race_data["office"],
                jurisdiction_name=race_data["jurisdiction_name"],
                election_date=race_data.get("election_date"),
                election_type=race_data.get("election_type"),
                candidates=candidates,
                notes=race_data.get("notes"),
            )
        )

    return LookupResult(
        zipcode=zipcode,
        races=races,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


MODEL = "claude-opus-4-8"

PROMPT_TEMPLATE = """You are researching upcoming local elections for a US zip code, \
for a nonpartisan voter-education tool. Prioritize official sources (state/county/city \
election authority websites, house.gov) before campaign sites or news.

Zip code: {zipcode}

Find, limited to these three race types:
1. The next mayoral election for the city containing this zip code (if the city has an \
elected mayor).
2. The next county-level election for the county containing this zip code.
3. The next U.S. House of Representatives election for the congressional district \
containing this zip code.

For each race type, find whichever election is soonest -- primary or general. If no \
upcoming race of that type exists, or the jurisdiction doesn't have one (e.g. no elected \
mayor), include it in your output with an empty candidates list and a note explaining why.

For each candidate, list their name, party (if known), incumbent status (if known), and \
2-4 short bullet points on their stated positions or priorities, each with a confidence \
level ("high", "medium", or "low") and the source URL(s) it came from. Only include a \
position if you found a real source for it -- never invent or infer one. If you found no \
documented positions for a candidate, give them an empty positions list.

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in \
exactly this shape:

{{
  "races": [
    {{
      "office": "mayor" | "county" | "us_house",
      "jurisdiction_name": "<string>",
      "election_date": "<YYYY-MM-DD or null>",
      "election_type": "primary" | "general" | null,
      "notes": "<string or null>",
      "candidates": [
        {{
          "name": "<string>",
          "party": "<string or null>",
          "incumbent": true | false | null,
          "positions": [
            {{
              "summary": "<string>",
              "confidence": "high" | "medium" | "low",
              "sources": [{{"url": "<string>", "title": "<string or null>"}}]
            }}
          ]
        }}
      ]
    }}
  ]
}}
"""


def find_local_elections(zipcode: str, client: "anthropic.Anthropic | None" = None) -> LookupResult:
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment before "
                "searching (e.g. `export ANTHROPIC_API_KEY=sk-ant-...`)."
            )
        client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(zipcode=zipcode)}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("The search request was refused. Try a different zip code or try again.")

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise ValueError("Model response contained no text output to parse.")

    return parse_lookup_response(zipcode, text_blocks[-1])
