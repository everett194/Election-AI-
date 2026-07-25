from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator, Literal

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


MODEL = "claude-sonnet-5"

OFFICES: tuple[str, ...] = ("mayor", "county", "us_house")

OFFICE_DESCRIPTIONS = {
    "mayor": "the next mayoral election for the city containing this zip code (if the "
    "city has an elected mayor)",
    "county": "the next county-level election for the county containing this zip code",
    "us_house": "the next U.S. House of Representatives election for the congressional "
    "district containing this zip code",
}

SINGLE_OFFICE_PROMPT_TEMPLATE = """You are researching an upcoming local election for a US \
zip code, for a nonpartisan voter-education tool. Prioritize official sources (state/county/ \
city election authority websites, house.gov) before campaign sites or news. Work \
efficiently -- a handful of well-chosen searches is enough; this does not need to be \
exhaustive.

Zip code: {zipcode}

Find {office_description}, whichever is soonest -- primary or general. If no upcoming \
race of this type exists, or the jurisdiction doesn't have one (e.g. no elected mayor), \
say so with a note explaining why and an empty candidates list.

For each candidate, list their name, party (if known), incumbent status (if known), and \
1-3 short bullet points on their stated positions or priorities, each with a confidence \
level ("high", "medium", or "low") and the source URL(s) it came from. Only include a \
position if you found a real source for it -- never invent or infer one. If you found no \
documented positions for a candidate, give them an empty positions list.

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in \
exactly this shape:

{{
  "races": [
    {{
      "office": "{office}",
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


def _search_one_office(zipcode: str, office: str, client: "anthropic.Anthropic") -> Race:
    prompt = SINGLE_OFFICE_PROMPT_TEMPLATE.format(
        zipcode=zipcode, office=office, office_description=OFFICE_DESCRIPTIONS[office]
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(f"The search for the {office} race was refused.")

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise ValueError(f"Model response for the {office} race contained no text output.")

    result = parse_lookup_response(zipcode, text_blocks[-1])
    if not result.races:
        raise ValueError(f"Model response for the {office} race did not include a race.")
    return result.races[0]


def iter_local_elections(
    zipcode: str,
    client: "anthropic.Anthropic | None" = None,
    offices: tuple[str, ...] = OFFICES,
) -> Iterator[Race]:
    """Yield each office's Race as soon as its search completes.

    Runs the same sequential per-office searches as find_local_elections, but
    yields incrementally so a caller (e.g. the UI) can display results as they
    arrive instead of waiting for all three. Pass a subset of `offices` to
    resume a search that was interrupted after some offices already completed.
    """
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment before "
                "searching (e.g. `export ANTHROPIC_API_KEY=sk-ant-...`)."
            )
        client = anthropic.Anthropic()

    for office in offices:
        try:
            yield _search_one_office(zipcode, office, client)
        except Exception as exc:
            yield Race(
                office=office,
                jurisdiction_name="Unknown",
                election_date=None,
                election_type=None,
                candidates=[],
                notes=f"Search for this race failed: {exc}",
            )


def find_local_elections(zipcode: str, client: "anthropic.Anthropic | None" = None) -> LookupResult:
    return LookupResult(
        zipcode=zipcode,
        races=list(iter_local_elections(zipcode, client)),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
