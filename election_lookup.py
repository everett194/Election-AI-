from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator, Literal

import anthropic

from questionnaire_scoring import QUESTIONS, QUESTIONS_BY_ID


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


_VALID_CONFIDENCES = {"high", "medium", "low"}


@dataclass
class CandidateIssuePosition:
    question_id: str
    position: int  # 1-5, same scale as the voter's own answers
    confidence: Literal["high", "medium", "low"]
    source: Source


@dataclass
class CandidateIssueProfile:
    candidate_name: str
    office: Literal["mayor", "county", "us_house"]
    positions: dict[str, int]  # question_id -> 1-5; feeds compute_candidate_compatibility directly
    sourced_positions: list[CandidateIssuePosition] = field(default_factory=list)

    def covered_categories(self) -> set[str]:
        """Categories with at least one sourced position -- the only categories
        it is honest to plot this candidate on."""
        return {QUESTIONS_BY_ID[qid].category for qid in self.positions}

    def covered_axes(self) -> tuple[bool, bool]:
        """(has_econ_coverage, has_social_coverage) -- whether at least one
        sourced position has a non-zero weight on that axis."""
        has_econ = any(QUESTIONS_BY_ID[qid].econ_weight > 0 for qid in self.positions)
        has_social = any(QUESTIONS_BY_ID[qid].social_weight > 0 for qid in self.positions)
        return has_econ, has_social


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


def parse_candidate_research_response(
    candidate_name: str, office: str, raw_text: str
) -> CandidateIssueProfile:
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "positions" not in data or not isinstance(data["positions"], list):
        raise ValueError("Model response JSON is missing a 'positions' array")

    sourced_positions: list[CandidateIssuePosition] = []
    positions_by_id: dict[str, int] = {}
    for pos_data in data["positions"]:
        if not isinstance(pos_data, dict):
            continue
        question_id = pos_data.get("question_id")
        if not isinstance(question_id, str) or question_id not in QUESTIONS_BY_ID:
            # Unknown/missing id -- skip rather than fail the whole response.
            continue

        if question_id in positions_by_id:
            continue

        position_value = pos_data.get("position")
        if (
            not isinstance(position_value, int)
            or isinstance(position_value, bool)
            or not (1 <= position_value <= 5)
        ):
            continue

        confidence = pos_data.get("confidence")
        if confidence not in _VALID_CONFIDENCES:
            continue

        source_data = pos_data.get("source")
        if not isinstance(source_data, dict):
            continue
        url = source_data.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue

        position = CandidateIssuePosition(
            question_id=question_id,
            position=position_value,
            confidence=confidence,
            source=Source(url=url, title=source_data.get("title")),
        )
        sourced_positions.append(position)
        positions_by_id[question_id] = position.position

    return CandidateIssueProfile(
        candidate_name=candidate_name,
        office=office,
        positions=positions_by_id,
        sourced_positions=sourced_positions,
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


CANDIDATE_RESEARCH_PROMPT_TEMPLATE = """You are researching one candidate's positions on a set \
of local-policy questions, for a nonpartisan voter-education tool. For EACH question below, only \
answer it if you find real, checkable evidence of this specific candidate's position -- never \
invent, infer, or guess based on party affiliation, endorsements, or general reputation. If you \
find no real source for a question, leave it out entirely.

When searching, prioritize sources in this order: (1) the candidate's own direct response to \
this questionnaire or a near-identical one, (2) established third-party candidate questionnaires \
such as Vote411 or Ballotpedia's Candidate Connection, (3) official statements or voting/public \
records, (4) reputable local news coverage of the candidate's platform or forum appearances, \
(5) the candidate's own campaign materials. Work efficiently -- a handful of well-chosen searches \
is enough; this does not need to be exhaustive.

Candidate: {candidate_name}{party_clause}{incumbent_clause}
Race: {office_description} ({jurisdiction_name}, zip code {zipcode})
{known_positions_clause}
For each of the following {question_count} questions, the candidate's position is on a 1-5 scale, \
where 1 means they fully favor the first approach, 5 means they fully favor the second approach, \
and 3 means their position is genuinely mixed/moderate between the two (only use 3 when you have \
real evidence of a mixed or moderate stance, not as a default for missing information).

{questions_block}

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in exactly \
this shape, including ONLY the questions you found real evidence for:

{{
  "positions": [
    {{
      "question_id": "<one of the question ids above>",
      "position": 1 | 2 | 3 | 4 | 5,
      "confidence": "high" | "medium" | "low",
      "source": {{"url": "<string>", "title": "<string or null>"}}
    }}
  ]
}}
"""


def _format_questions_block() -> str:
    lines = []
    for question in QUESTIONS:
        lines.append(
            f"- id: {question.id}\n"
            f"  question: {question.text}\n"
            f"  approach 1 (position 1-2): {question.approach_1}\n"
            f"  approach 2 (position 4-5): {question.approach_2}"
        )
    return "\n".join(lines)


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


def _call_model_for_text(
    client: "anthropic.Anthropic", prompt: str, max_tokens: int, refusal_subject: str
) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(f"The search for {refusal_subject} was refused.")

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise ValueError(f"Model response for {refusal_subject} contained no text output.")

    return text_blocks[-1]


def _search_one_office(zipcode: str, office: str, client: "anthropic.Anthropic") -> Race:
    prompt = SINGLE_OFFICE_PROMPT_TEMPLATE.format(
        zipcode=zipcode, office=office, office_description=OFFICE_DESCRIPTIONS[office]
    )
    text = _call_model_for_text(client, prompt, max_tokens=3000, refusal_subject=f"the {office} race")

    result = parse_lookup_response(zipcode, text)
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


def research_candidate_positions(
    zipcode: str,
    office: str,
    jurisdiction_name: str,
    candidate: Candidate,
    client: "anthropic.Anthropic | None" = None,
) -> CandidateIssueProfile:
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment before "
                "searching (e.g. `export ANTHROPIC_API_KEY=sk-ant-...`)."
            )
        client = anthropic.Anthropic()

    party_clause = f", {candidate.party}" if candidate.party else ""
    incumbent_clause = " (incumbent)" if candidate.incumbent else ""
    if candidate.positions:
        known_lines = "\n".join(
            f"- {position.summary} (confidence: {position.confidence})"
            for position in candidate.positions
        )
        known_positions_clause = (
            "\nPositions already documented for this candidate, for context "
            f"(you may find more specific evidence for the questions below):\n{known_lines}\n"
        )
    else:
        known_positions_clause = ""

    prompt = CANDIDATE_RESEARCH_PROMPT_TEMPLATE.format(
        candidate_name=candidate.name,
        party_clause=party_clause,
        incumbent_clause=incumbent_clause,
        office_description=OFFICE_DESCRIPTIONS[office],
        jurisdiction_name=jurisdiction_name,
        zipcode=zipcode,
        known_positions_clause=known_positions_clause,
        question_count=len(QUESTIONS),
        questions_block=_format_questions_block(),
    )

    text = _call_model_for_text(
        client, prompt, max_tokens=4000, refusal_subject=f"{candidate.name}'s positions"
    )

    return parse_candidate_research_response(candidate.name, office, text)
