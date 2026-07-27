from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterator, Literal, TypeVar

import anthropic

import tavily_search
from questionnaire_scoring import QUESTIONS, QUESTIONS_BY_ID

_T = TypeVar("_T")


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
    confidence: str  # one of several taxonomies depending on how this was produced --
    # "high"/"medium"/"low" (race-search style), "explicit"/"strong_inference"/
    # "weak_inference" (Tavily evidence-backed), or "speculative" (no source at all,
    # a fallback guess -- see research_candidates_for_race_with_fallback)
    source: "Source | None" = None  # None for a speculative (unsourced) position


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


def _parse_sourced_positions(
    positions_data: "list",
) -> "tuple[dict[str, int], list[CandidateIssuePosition]]":
    """Validates and converts a raw `positions` JSON array (shared by both the
    single-candidate and batched-per-race response shapes) into the
    (question_id -> 1-5, sourced positions list) pair every caller needs.
    Any entry with a missing/malformed field is skipped rather than failing
    the whole response over one bad entry.
    """
    sourced_positions: list[CandidateIssuePosition] = []
    positions_by_id: dict[str, int] = {}
    for pos_data in positions_data:
        if not isinstance(pos_data, dict):
            continue
        question_id = pos_data.get("question_id")
        if not isinstance(question_id, str) or question_id not in QUESTIONS_BY_ID:
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

    return positions_by_id, sourced_positions


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

    positions_by_id, sourced_positions = _parse_sourced_positions(data["positions"])

    return CandidateIssueProfile(
        candidate_name=candidate_name,
        office=office,
        positions=positions_by_id,
        sourced_positions=sourced_positions,
    )


def parse_candidates_research_response(
    office: str, candidate_names: "list[str]", raw_text: str
) -> "dict[str, CandidateIssueProfile]":
    """Batched counterpart to parse_candidate_research_response: parses one
    response covering multiple candidates in the same race. Entries for an
    unrecognized or duplicate candidate name are skipped rather than failing
    the whole response.
    """
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "candidates" not in data or not isinstance(data["candidates"], list):
        raise ValueError("Model response JSON is missing a 'candidates' array")

    valid_names = set(candidate_names)
    profiles: dict[str, CandidateIssueProfile] = {}
    for cand_data in data["candidates"]:
        if not isinstance(cand_data, dict):
            continue
        name = cand_data.get("name")
        if not isinstance(name, str) or name not in valid_names or name in profiles:
            continue
        positions_data = cand_data.get("positions")
        if not isinstance(positions_data, list):
            continue
        positions_by_id, sourced_positions = _parse_sourced_positions(positions_data)
        profiles[name] = CandidateIssueProfile(
            candidate_name=name,
            office=office,
            positions=positions_by_id,
            sourced_positions=sourced_positions,
        )

    return profiles


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


CANDIDATES_RESEARCH_PROMPT_TEMPLATE = """You are researching multiple candidates' positions on a \
set of local-policy questions, for a nonpartisan voter-education tool. For EACH candidate and EACH \
question below, only answer it if you find real, checkable evidence of that specific candidate's \
position -- never invent, infer, or guess based on party affiliation, endorsements, or general \
reputation. If you find no real source for a question, leave it out entirely for that candidate.

When searching, prioritize sources in this order: (1) each candidate's own direct response to \
this questionnaire or a near-identical one, (2) established third-party candidate questionnaires \
such as Vote411 or Ballotpedia's Candidate Connection, (3) official statements or voting/public \
records, (4) reputable local news coverage of a candidate's platform or forum appearances, \
(5) a candidate's own campaign materials. Work efficiently -- research all {candidate_count} \
candidates below in one pass with a small, shared budget of searches total (not per candidate); \
pick a few of the most likely-to-work searches rather than being exhaustive, and prioritize the \
highest-signal source tiers above over trying every candidate on every tier.

Race: {office_description} ({jurisdiction_name}, zip code {zipcode})

Candidates:
{candidates_block}

For each of the following {question_count} questions, a candidate's position is on a 1-5 scale, \
where 1 means they fully favor the first approach, 5 means they fully favor the second approach, \
and 3 means their position is genuinely mixed/moderate between the two (only use 3 when you have \
real evidence of a mixed or moderate stance for that specific candidate, not as a default for \
missing information).

{questions_block}

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in exactly \
this shape, with one entry per candidate listed above (using their name exactly as given), \
including ONLY the questions you found real evidence for:

{{
  "candidates": [
    {{
      "name": "<one of the candidate names above, exactly as given>",
      "positions": [
        {{
          "question_id": "<one of the question ids above>",
          "position": 1 | 2 | 3 | 4 | 5,
          "confidence": "high" | "medium" | "low",
          "source": {{"url": "<string>", "title": "<string or null>"}}
        }}
      ]
    }}
  ]
}}
"""


def _format_candidates_block(candidates: "list[Candidate]") -> str:
    blocks = []
    for candidate in candidates:
        party_clause = f", {candidate.party}" if candidate.party else ""
        incumbent_clause = " (incumbent)" if candidate.incumbent else ""
        header = f"- {candidate.name}{party_clause}{incumbent_clause}"
        if candidate.positions:
            known_lines = "\n".join(
                f"  - {position.summary} (confidence: {position.confidence})"
                for position in candidate.positions
            )
            blocks.append(f"{header}\n  Already documented, for context:\n{known_lines}")
        else:
            blocks.append(header)
    return "\n".join(blocks)


CANDIDATE_PREDICTION_PROMPT_TEMPLATE = """You are estimating how {candidate_count} candidates in a \
local race would likely answer a set of local-policy questions, for a nonpartisan voter-education \
tool. This is a fast ESTIMATE, not verified research -- use your general knowledge of each \
candidate's party affiliation, incumbency, any positions already documented below, typical \
positions for candidates of that party/background in similar local races, and your own reasoning. \
Do not use any tools or search the web; answer from what you already know and can reasonably \
infer. Every candidate should get an answer for every question below -- if you have no specific \
information on a candidate, make your best reasonable estimate from party/background rather than \
skipping it.

Race: {office_description} ({jurisdiction_name}, zip code {zipcode})

Candidates:
{candidates_block}

For each of the following {question_count} questions, a candidate's position is on a 1-5 scale, \
where 1 means they fully favor the first approach, 5 means they fully favor the second approach, \
and 3 means a genuinely moderate or uncertain position.

{questions_block}

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in exactly \
this shape, with one entry per candidate listed above (using their name exactly as given) and an \
estimated answer for every one of the {question_count} questions:

{{
  "candidates": [
    {{
      "name": "<one of the candidate names above, exactly as given>",
      "positions": [
        {{"question_id": "<one of the question ids above>", "position": 1 | 2 | 3 | 4 | 5}}
      ]
    }}
  ]
}}
"""


def _parse_predicted_positions(positions_data: "list") -> "dict[str, int]":
    positions_by_id: dict[str, int] = {}
    for pos_data in positions_data:
        if not isinstance(pos_data, dict):
            continue
        question_id = pos_data.get("question_id")
        if not isinstance(question_id, str) or question_id not in QUESTIONS_BY_ID:
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
        positions_by_id[question_id] = position_value
    return positions_by_id


def parse_candidates_prediction_response(
    office: str, candidate_names: "list[str]", raw_text: str
) -> "dict[str, CandidateIssueProfile]":
    """Parses the fast, non-sourced candidate-estimate response into
    CandidateIssueProfile objects with `sourced_positions=[]` (there are no
    real sources for an estimate) -- the same return shape as
    research_candidates_for_race, so callers can use either interchangeably.
    """
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "candidates" not in data or not isinstance(data["candidates"], list):
        raise ValueError("Model response JSON is missing a 'candidates' array")

    valid_names = set(candidate_names)
    profiles: dict[str, CandidateIssueProfile] = {}
    for cand_data in data["candidates"]:
        if not isinstance(cand_data, dict):
            continue
        name = cand_data.get("name")
        if not isinstance(name, str) or name not in valid_names or name in profiles:
            continue
        positions_data = cand_data.get("positions")
        if not isinstance(positions_data, list):
            continue
        positions_by_id = _parse_predicted_positions(positions_data)
        profiles[name] = CandidateIssueProfile(
            candidate_name=name, office=office, positions=positions_by_id, sourced_positions=[]
        )

    return profiles


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
1-3 short bullet points about their record, background, and stated positions or priorities. \
Prefer real, sourced statements when you find them -- mark those "high" or "medium" \
confidence with the source URL(s) they came from. If you cannot find a specific sourced \
position on an issue, still give at least one brief, honest line based on whatever you do \
know (party affiliation, general political alignment, professional background, prior public \
record, or simply "no public statements found on this candidate's priorities") rather than \
leaving the candidate blank -- mark that "low" confidence with an empty sources list, and \
phrase it as an inference, not a fact (e.g. "Likely favors ... based on party affiliation" \
rather than "Supports ..."). Every candidate should end up with at least one bullet point, \
even if it is only a low-confidence one.

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
    client: "anthropic.Anthropic",
    prompt: str,
    max_tokens: int,
    refusal_subject: str,
    use_web_search: bool = True,
    max_uses: int = 5,
) -> str:
    kwargs: dict = dict(
        model=MODEL,
        max_tokens=max_tokens,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}]
    response = client.messages.create(**kwargs)

    if response.stop_reason == "refusal":
        raise RuntimeError(f"The search for {refusal_subject} was refused.")

    text_blocks = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and (block.text or "").strip()
    ]
    if not text_blocks:
        raise ValueError(f"Model response for {refusal_subject} contained no text output.")

    return text_blocks[-1]


def _call_model_and_parse(
    client: "anthropic.Anthropic",
    prompt: str,
    max_tokens: int,
    refusal_subject: str,
    parse: "Callable[[str], _T]",
    use_web_search: bool = True,
    max_uses: int = 5,
) -> "_T":
    """Calls the model and parses its response, retrying once if the first
    attempt produced no usable text or text that wasn't valid JSON --
    occasional malformed output from a single model call is common enough
    that one retry meaningfully improves reliability without an open-ended
    retry loop.
    """
    last_error: ValueError | None = None
    for _ in range(2):
        try:
            text = _call_model_for_text(
                client,
                prompt,
                max_tokens,
                refusal_subject,
                use_web_search=use_web_search,
                max_uses=max_uses,
            )
            return parse(text)
        except ValueError as exc:
            last_error = exc
    raise last_error


def _search_one_office(zipcode: str, office: str, client: "anthropic.Anthropic") -> Race:
    prompt = SINGLE_OFFICE_PROMPT_TEMPLATE.format(
        zipcode=zipcode, office=office, office_description=OFFICE_DESCRIPTIONS[office]
    )

    def parse(text: str) -> Race:
        result = parse_lookup_response(zipcode, text)
        if not result.races:
            raise ValueError(f"Model response for the {office} race did not include a race.")
        return result.races[0]

    return _call_model_and_parse(
        client, prompt, max_tokens=3000, refusal_subject=f"the {office} race", parse=parse
    )


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

    def parse(text: str) -> CandidateIssueProfile:
        return parse_candidate_research_response(candidate.name, office, text)

    return _call_model_and_parse(
        client, prompt, max_tokens=4000, refusal_subject=f"{candidate.name}'s positions", parse=parse
    )


def research_candidates_for_race(
    zipcode: str,
    office: str,
    jurisdiction_name: str,
    candidates: "list[Candidate]",
    client: "anthropic.Anthropic | None" = None,
) -> "dict[str, CandidateIssueProfile]":
    """Batched counterpart to research_candidate_positions: one search call
    covering every candidate in a race, instead of one call per candidate.
    Cuts the number of sequential candidate-research calls from N (one per
    candidate) down to 1 per race, at the cost of somewhat thinner per-
    candidate coverage than researching each one individually.

    Returns a dict keyed by candidate name; a candidate absent from the
    result (e.g. the model found nothing at all for them) should be treated
    the same as a profile with zero sourced positions.
    """
    if not candidates:
        return {}
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment before "
                "searching (e.g. `export ANTHROPIC_API_KEY=sk-ant-...`)."
            )
        client = anthropic.Anthropic()

    candidate_names = [candidate.name for candidate in candidates]

    prompt = CANDIDATES_RESEARCH_PROMPT_TEMPLATE.format(
        candidate_count=len(candidates),
        office_description=OFFICE_DESCRIPTIONS[office],
        jurisdiction_name=jurisdiction_name,
        zipcode=zipcode,
        candidates_block=_format_candidates_block(candidates),
        question_count=len(QUESTIONS),
        questions_block=_format_questions_block(),
    )

    def parse(text: str) -> "dict[str, CandidateIssueProfile]":
        return parse_candidates_research_response(office, candidate_names, text)

    return _call_model_and_parse(
        client,
        prompt,
        max_tokens=min(8000, 3000 + 1500 * len(candidates)),
        refusal_subject=f"candidates in the {office} race",
        parse=parse,
        max_uses=4,
    )


def predict_candidates_for_race(
    zipcode: str,
    office: str,
    jurisdiction_name: str,
    candidates: "list[Candidate]",
    client: "anthropic.Anthropic | None" = None,
) -> "dict[str, CandidateIssueProfile]":
    """Fast, non-web-search estimate of every candidate's likely answers to
    all 20 questions, from the model's own knowledge and reasoning (party,
    incumbency, any positions already documented, typical positions for
    similar candidates) rather than fresh research. Skips the web_search
    tool entirely, so this is much faster than research_candidates_for_race
    -- at the direct cost of being an estimate, not a sourced fact. Every
    returned position is unverified and should be treated as such by
    callers/UI.

    Same return shape as research_candidates_for_race (dict keyed by
    candidate name, CandidateIssueProfile with an empty sourced_positions
    list) so the two are interchangeable for callers.
    """
    if not candidates:
        return {}
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment before "
                "searching (e.g. `export ANTHROPIC_API_KEY=sk-ant-...`)."
            )
        client = anthropic.Anthropic()

    candidate_names = [candidate.name for candidate in candidates]

    prompt = CANDIDATE_PREDICTION_PROMPT_TEMPLATE.format(
        candidate_count=len(candidates),
        office_description=OFFICE_DESCRIPTIONS[office],
        jurisdiction_name=jurisdiction_name,
        zipcode=zipcode,
        candidates_block=_format_candidates_block(candidates),
        question_count=len(QUESTIONS),
        questions_block=_format_questions_block(),
    )

    def parse(text: str) -> "dict[str, CandidateIssueProfile]":
        return parse_candidates_prediction_response(office, candidate_names, text)

    return _call_model_and_parse(
        client,
        prompt,
        max_tokens=min(6000, 2000 + 1000 * len(candidates)),
        refusal_subject=f"candidate estimates for the {office} race",
        parse=parse,
        use_web_search=False,
    )


# --- Tavily-backed evidence research -----------------------------------
#
# Two-stage pipeline: (1) fan out several search queries per candidate to
# the Tavily search API in parallel and collect real evidence, (2) one
# Claude call per race that reads ONLY that evidence and produces a sourced,
# confidence-tagged answer per question -- never from party affiliation,
# endorsements, demographics, or absence of information alone. The Claude
# call skips the web_search tool (use_web_search=False) since the evidence
# is already gathered, which is what keeps this fast.

_VALID_INFERENCE_LEVELS = {"explicit", "strong_inference", "weak_inference"}


def _candidate_search_queries(candidate_name: str, office: str, jurisdiction_name: str) -> "list[str]":
    office_label = {
        "mayor": "mayor",
        "county": "county",
        "us_house": "U.S. House",
    }.get(office, office)
    return [
        f"{candidate_name} {jurisdiction_name} {office_label} Vote411",
        f"{candidate_name} {jurisdiction_name} {office_label} Ballotpedia Candidate Connection",
        f"{candidate_name} {jurisdiction_name} {office_label} official statement voting record",
        f"{candidate_name} {jurisdiction_name} {office_label} campaign positions priorities",
    ]


def _format_evidence_block(
    candidate_name: str, results_by_query: "dict[str, list[tavily_search.SearchResult]]"
) -> str:
    all_results = tavily_search.dedupe_by_url(
        [result for results in results_by_query.values() for result in results]
    )
    if not all_results:
        return f"### {candidate_name}\nNo search results found."

    lines = [f"### {candidate_name}"]
    for result in all_results[:12]:  # cap so the prompt stays a reasonable size
        snippet = result.content[:600]
        lines.append(f"- URL: {result.url}\n  Title: {result.title}\n  Excerpt: {snippet}")
    return "\n".join(lines)


CANDIDATE_EVIDENCE_EXTRAPOLATION_PROMPT_TEMPLATE = """You are analyzing pre-gathered web search \
evidence to determine {candidate_count} candidates' likely positions on a set of local-policy \
questions, for a nonpartisan voter-education tool. Use ONLY the evidence provided below for each \
candidate -- do not use outside knowledge, and do not search further.

For each candidate and each question, classify your answer's confidence as exactly one of:
- "explicit": the evidence contains a direct, specific statement from or about the candidate on \
this exact question.
- "strong_inference": the evidence strongly implies a position (e.g. a closely related vote, \
statement, or documented record) even without an exact direct quote on this precise question.
- "weak_inference": only a loose or partial signal exists (e.g. a general priority mentioned once, \
tangential to this specific question).

Do NOT answer a question at all if the only basis would be the candidate's party affiliation \
alone, an endorsement alone, demographic assumptions, or the simple absence of information -- \
these are never acceptable evidence on their own. If nothing in the evidence meets at least \
"weak_inference" for a question, leave that question out entirely for that candidate.

Race: {office_description} ({jurisdiction_name}, zip code {zipcode})

Evidence found for each candidate:

{evidence_block}

For each of the following {question_count} questions, a candidate's position is on a 1-5 scale, \
where 1 means they fully favor the first approach, 5 means they fully favor the second approach, \
and 3 means a genuinely mixed/moderate position supported by the evidence.

{questions_block}

Respond with ONLY a single JSON object (no markdown fences, no prose before or after) in exactly \
this shape, with one entry per candidate listed above (using their name exactly as given), \
including a question only when the evidence meets at least "weak_inference", and citing the \
specific URL from the evidence above that supports each answer:

{{
  "candidates": [
    {{
      "name": "<one of the candidate names above, exactly as given>",
      "positions": [
        {{
          "question_id": "<one of the question ids above>",
          "position": 1 | 2 | 3 | 4 | 5,
          "confidence": "explicit" | "strong_inference" | "weak_inference",
          "source_url": "<one of the URLs from the evidence above>"
        }}
      ]
    }}
  ]
}}
"""


def _parse_evidence_positions(
    positions_data: "list",
) -> "tuple[dict[str, int], list[CandidateIssuePosition]]":
    positions_by_id: dict[str, int] = {}
    sourced_positions: list[CandidateIssuePosition] = []
    for pos_data in positions_data:
        if not isinstance(pos_data, dict):
            continue
        question_id = pos_data.get("question_id")
        if not isinstance(question_id, str) or question_id not in QUESTIONS_BY_ID:
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
        if confidence not in _VALID_INFERENCE_LEVELS:
            continue

        source_url = pos_data.get("source_url")
        if not isinstance(source_url, str) or not source_url.startswith(("http://", "https://")):
            continue

        sourced_positions.append(
            CandidateIssuePosition(
                question_id=question_id,
                position=position_value,
                confidence=confidence,
                source=Source(url=source_url, title=None),
            )
        )
        positions_by_id[question_id] = position_value

    return positions_by_id, sourced_positions


def parse_candidates_evidence_response(
    office: str, candidate_names: "list[str]", raw_text: str
) -> "dict[str, CandidateIssueProfile]":
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "candidates" not in data or not isinstance(data["candidates"], list):
        raise ValueError("Model response JSON is missing a 'candidates' array")

    valid_names = set(candidate_names)
    profiles: dict[str, CandidateIssueProfile] = {}
    for cand_data in data["candidates"]:
        if not isinstance(cand_data, dict):
            continue
        name = cand_data.get("name")
        if not isinstance(name, str) or name not in valid_names or name in profiles:
            continue
        positions_data = cand_data.get("positions")
        if not isinstance(positions_data, list):
            continue
        positions_by_id, sourced_positions = _parse_evidence_positions(positions_data)
        profiles[name] = CandidateIssueProfile(
            candidate_name=name, office=office, positions=positions_by_id, sourced_positions=sourced_positions
        )

    return profiles


def research_candidates_via_tavily(
    zipcode: str,
    office: str,
    jurisdiction_name: str,
    candidates: "list[Candidate]",
    client: "anthropic.Anthropic | None" = None,
) -> "dict[str, CandidateIssueProfile]":
    """Real, sourced candidate research via Tavily search + one Claude
    synthesis call per race. Faster than research_candidates_for_race
    because Claude reads pre-fetched evidence directly instead of running
    its own agentic web_search loop, and the Tavily fan-out itself runs in
    parallel (safe here -- Tavily is a plain search API, not subject to the
    Anthropic-call rate-limit issue this project hit with parallel Claude
    calls; see git history).
    """
    if not candidates:
        return {}
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment before "
                "searching (e.g. `export ANTHROPIC_API_KEY=sk-ant-...`)."
            )
        client = anthropic.Anthropic()

    queries_by_candidate: dict[str, list[str]] = {
        candidate.name: _candidate_search_queries(candidate.name, office, jurisdiction_name)
        for candidate in candidates
    }
    all_queries = [query for queries in queries_by_candidate.values() for query in queries]
    results_by_query = tavily_search.search_many(all_queries, max_results_per_query=4)

    evidence_block = "\n\n".join(
        _format_evidence_block(
            candidate.name,
            {query: results_by_query.get(query, []) for query in queries_by_candidate[candidate.name]},
        )
        for candidate in candidates
    )

    prompt = CANDIDATE_EVIDENCE_EXTRAPOLATION_PROMPT_TEMPLATE.format(
        candidate_count=len(candidates),
        office_description=OFFICE_DESCRIPTIONS[office],
        jurisdiction_name=jurisdiction_name,
        zipcode=zipcode,
        evidence_block=evidence_block,
        question_count=len(QUESTIONS),
        questions_block=_format_questions_block(),
    )

    candidate_names = [candidate.name for candidate in candidates]

    def parse(text: str) -> "dict[str, CandidateIssueProfile]":
        return parse_candidates_evidence_response(office, candidate_names, text)

    return _call_model_and_parse(
        client,
        prompt,
        max_tokens=min(8000, 3000 + 1500 * len(candidates)),
        refusal_subject=f"candidate evidence analysis for the {office} race",
        parse=parse,
        use_web_search=False,
    )


def research_candidates_for_race_with_fallback(
    zipcode: str,
    office: str,
    jurisdiction_name: str,
    candidates: "list[Candidate]",
    client: "anthropic.Anthropic | None" = None,
) -> "dict[str, CandidateIssueProfile]":
    """Combines real, sourced research (research_candidates_via_tavily) with
    a speculative fallback (predict_candidates_for_race) so every candidate
    ends up with a full or near-full profile and actually shows up on the
    comparison charts, instead of being silently excluded because local-race
    web coverage is often thin. A sourced answer always wins over a
    speculative one for the same question; speculative positions are tagged
    confidence="speculative" with no source, so the UI can (and does) label
    them as an unverified guess rather than presenting them as fact.

    Speculation is only requested for candidates whose sourced profile is
    missing at least one of the 20 questions -- a candidate with full real
    coverage never gets a speculative call at all.
    """
    if not candidates:
        return {}

    sourced_profiles = research_candidates_via_tavily(zipcode, office, jurisdiction_name, candidates, client)

    needs_speculation = [
        candidate
        for candidate in candidates
        if len(sourced_profiles.get(candidate.name, CandidateIssueProfile(candidate.name, office, {}, [])).positions)
        < len(QUESTIONS)
    ]
    speculative_profiles: dict[str, CandidateIssueProfile] = {}
    if needs_speculation:
        speculative_profiles = predict_candidates_for_race(
            zipcode, office, jurisdiction_name, needs_speculation, client
        )

    merged: dict[str, CandidateIssueProfile] = {}
    for candidate in candidates:
        sourced = sourced_profiles.get(candidate.name)
        positions: dict[str, int] = dict(sourced.positions) if sourced else {}
        sourced_positions: list[CandidateIssuePosition] = list(sourced.sourced_positions) if sourced else []

        speculative = speculative_profiles.get(candidate.name)
        if speculative:
            for question_id, position_value in speculative.positions.items():
                if question_id in positions:
                    continue  # real evidence already covers this question -- keep it
                positions[question_id] = position_value
                sourced_positions.append(
                    CandidateIssuePosition(
                        question_id=question_id,
                        position=position_value,
                        confidence="speculative",
                        source=None,
                    )
                )

        merged[candidate.name] = CandidateIssueProfile(
            candidate_name=candidate.name,
            office=office,
            positions=positions,
            sourced_positions=sourced_positions,
        )

    return merged
