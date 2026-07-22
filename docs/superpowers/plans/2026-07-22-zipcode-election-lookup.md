# Zip Code Live Election Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `userinterface.py`'s zip code input to a real, live lookup of the next mayoral, county, and U.S. House elections (primary or general) for that zip code, showing candidates and sourced/confidence-labeled position summaries.

**Architecture:** A new `election_lookup.py` module owns all Anthropic API interaction (web search tool + JSON parsing into typed records); `userinterface.py` only renders what it's given. See `docs/superpowers/specs/2026-07-22-zipcode-election-lookup-design.md` for the full design rationale.

**Tech Stack:** Python 3.12, `anthropic` SDK (`client.messages.create` with the `web_search_20260209` server tool, model `claude-opus-4-8`), Streamlit, `pytest` for unit tests (no live API calls in automated tests).

## Global Constraints

- Model: `claude-opus-4-8` (per project default; no user request for a different model).
- Web search tool type: `web_search_20260209` (dynamic filtering, supported on Opus 4.8).
- Requires `ANTHROPIC_API_KEY` in the environment at runtime — never hardcoded, never logged.
- No fabricated positions: an empty result renders as "No documented position found," never a guess (per `datamechanism.md` Failure Handling and the design spec's Accuracy Handling section).
- Every position carries a confidence label (`high`/`medium`/`low`) and source URL(s).
- No live API calls inside automated tests — mock the Anthropic client with fixed JSON fixtures.

---

### Task 1: Data models and JSON parsing

**Files:**
- Create: `election_lookup.py` (models + `parse_lookup_response` function only in this task)
- Test: `test_election_lookup.py`

**Interfaces:**
- Produces: `Source(url: str, title: str | None)`, `Position(summary: str, confidence: Literal["high","medium","low"], sources: list[Source])`, `Candidate(name: str, party: str | None, incumbent: bool | None, positions: list[Position])`, `Race(office: Literal["mayor","county","us_house"], jurisdiction_name: str, election_date: str | None, election_type: Literal["primary","general"] | None, candidates: list[Candidate], notes: str | None)`, `LookupResult(zipcode: str, races: list[Race], retrieved_at: str)`, and `parse_lookup_response(zipcode: str, raw_text: str) -> LookupResult` which raises `ValueError` on malformed/non-JSON input.

- [ ] **Step 1: Write the failing tests**

```python
# test_election_lookup.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest test_election_lookup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'election_lookup'` (or `ImportError`)

- [ ] **Step 3: Write the implementation**

```python
# election_lookup.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest test_election_lookup.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add election_lookup.py test_election_lookup.py
git commit -m "Add data models and JSON parsing for election lookup"
```

---

### Task 2: Anthropic API call with web search

**Files:**
- Modify: `election_lookup.py` (add `find_local_elections`)
- Modify: `test_election_lookup.py` (add mocked-client tests)

**Interfaces:**
- Consumes: `parse_lookup_response(zipcode, raw_text) -> LookupResult` from Task 1.
- Produces: `find_local_elections(zipcode: str, client: "anthropic.Anthropic | None" = None) -> LookupResult`. Raises `RuntimeError` if `ANTHROPIC_API_KEY` is unset and no client was passed in, and `ValueError` (propagated from `parse_lookup_response`) on malformed model output.

- [ ] **Step 1: Write the failing tests**

```python
# Append to test_election_lookup.py
import os
from unittest.mock import MagicMock, patch

from election_lookup import find_local_elections


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest test_election_lookup.py -v`
Expected: FAIL with `ImportError: cannot import name 'find_local_elections'`

- [ ] **Step 3: Write the implementation**

```python
# Append to election_lookup.py
import os

import anthropic


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest test_election_lookup.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add election_lookup.py test_election_lookup.py
git commit -m "Add live web-search-backed election lookup via Anthropic API"
```

---

### Task 3: Streamlit UI wiring

**Files:**
- Modify: `userinterface.py`

**Interfaces:**
- Consumes: `find_local_elections(zipcode: str) -> LookupResult` and the `Race`/`Candidate`/`Position`/`Source` dataclasses from `election_lookup.py` (Tasks 1-2).

- [ ] **Step 1: Replace the stub body with the real search flow**

```python
"""
userinterface.py

Streamlit front end that collects a US zip code and looks up the next
mayoral, county, and U.S. House elections for it via election_lookup.py.

Run with:
    streamlit run userinterface.py
"""

import re

import streamlit as st

from election_lookup import LookupResult, find_local_elections

ZIP_PATTERN = re.compile(r"^\d{5}$")

OFFICE_LABELS = {
    "mayor": "Mayoral",
    "county": "County",
    "us_house": "U.S. House",
}


def is_valid_zipcode(zipcode: str) -> bool:
    """Return True if zipcode is a 5-digit US zip code."""
    return bool(ZIP_PATTERN.match(zipcode.strip()))


def render_result(result: LookupResult) -> None:
    st.caption(f"Retrieved at {result.retrieved_at}")
    by_office = {race.office: race for race in result.races}

    for office in ("mayor", "county", "us_house"):
        race = by_office.get(office)
        with st.expander(OFFICE_LABELS[office], expanded=True):
            if race is None:
                st.write("No information found for this race type.")
                continue

            if race.election_date:
                st.write(f"**{race.jurisdiction_name}** — {race.election_date} ({race.election_type})")
            else:
                st.write(f"**{race.jurisdiction_name}**")

            if race.notes:
                st.info(race.notes)

            if not race.candidates:
                st.write("No candidates found.")
                continue

            for candidate in race.candidates:
                header = candidate.name
                if candidate.party:
                    header += f" ({candidate.party})"
                if candidate.incumbent:
                    header += " — incumbent"
                st.markdown(f"**{header}**")

                if not candidate.positions:
                    st.write("No documented position found.")
                    continue

                for position in candidate.positions:
                    badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(position.confidence, "⚪")
                    st.write(f"{badge} {position.summary} _(confidence: {position.confidence})_")
                    for source in position.sources:
                        st.markdown(f"  - [{source.title or source.url}]({source.url})")


def main() -> None:
    st.title("Election AI - User Interface")
    st.warning(
        "Results are AI-assisted best-effort research from a single automated web "
        "search and are not guaranteed complete or error-free. Verify anything "
        "important via the linked official sources."
    )
    st.write("Enter your zip code to find your next local elections.")

    zipcode = st.text_input("Zip code", placeholder="e.g. 90210", max_chars=5)
    search_clicked = st.button("Find my elections")

    if "lookup_cache" not in st.session_state:
        st.session_state.lookup_cache = {}

    if zipcode and not is_valid_zipcode(zipcode):
        st.error("Please enter a valid 5-digit zip code (e.g. 90210).")
        return

    if search_clicked and zipcode:
        if zipcode not in st.session_state.lookup_cache:
            with st.spinner("Searching official sources..."):
                try:
                    st.session_state.lookup_cache[zipcode] = find_local_elections(zipcode)
                except Exception as exc:
                    st.error(f"Search failed: {exc}")
                    return

    if zipcode in st.session_state.lookup_cache:
        render_result(st.session_state.lookup_cache[zipcode])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the module still imports and compiles cleanly**

Run: `python3 -m py_compile userinterface.py election_lookup.py`
Expected: no output, exit code 0

- [ ] **Step 3: Run a headless Streamlit smoke test**

Run:
```bash
(streamlit run userinterface.py --server.headless true --server.port 8765 > /tmp/streamlit_ui.log 2>&1 &) && sleep 6 && curl -s -o /dev/null -w "HTTP status: %{http_code}\n" http://localhost:8765 && cat /tmp/streamlit_ui.log && pkill -f "streamlit run userinterface.py"
```
Expected: `HTTP status: 200` and no Python tracebacks in the log

- [ ] **Step 4: Commit**

```bash
git add userinterface.py
git commit -m "Wire zip code UI to live election_lookup search results"
```

---

### Task 4: Dependencies and manual live verification

**Files:**
- Create: `requirements.txt`
- Modify: none (manual verification step, no code change)

**Interfaces:**
- None (packaging + manual smoke test only).

- [ ] **Step 1: Write requirements.txt**

```
streamlit
anthropic
pytest
```

- [ ] **Step 2: Install and confirm the automated test suite passes**

Run: `pip3 install -r requirements.txt && python3 -m pytest test_election_lookup.py -v`
Expected: all tests pass (7 total from Tasks 1-2)

- [ ] **Step 3: Commit dependency file**

```bash
git add requirements.txt
git commit -m "Add requirements.txt for the election lookup app"
```

- [ ] **Step 4: Manual live smoke test (requires a real ANTHROPIC_API_KEY)**

This step cannot be automated or verified without a real API key and real spend, so it is manual:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # user's own key
python3 -c "from election_lookup import find_local_elections; r = find_local_elections('20500'); print(r)"
```

Expected: a `LookupResult` prints with at least one race populated, plausible (future) election dates, and source URLs that look real. If the output is empty across all three race types or dates are clearly wrong, treat the prompt or model behavior as needing revision before considering this done.
