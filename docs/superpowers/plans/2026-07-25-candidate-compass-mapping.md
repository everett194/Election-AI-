# Candidate Compass/Radar Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a voter research one candidate's real, sourced positions on the 20 questionnaire questions, on demand, and see that candidate overlaid on the voter's own radar and compass charts.

**Architecture:** `election_lookup.py` gains a new per-candidate research function (one Anthropic call with the `web_search` tool, same shape as the existing per-office race search) and two new dataclasses. `questionnaire_ui.py` triggers that research on button click, caches the result in `st.session_state`, and overlays mapped candidates on the existing (extended) radar/compass chart functions. `userinterface.py` passes the relevant `Race` (with its candidates) into `render_questionnaire`.

**Tech Stack:** Python 3.10+, Streamlit, `anthropic` SDK (`web_search` tool), Altair (charts), pytest.

## Global Constraints

- Model: `"claude-sonnet-5"` (module constant `MODEL` in `election_lookup.py`, reused, not duplicated).
- Never fabricate, infer, or guess a candidate position from party/reputation/endorsements — only record a position when the research finds real, checkable evidence with a source URL. Unanswered questions are omitted, never defaulted to neutral.
- Source-tier preference order (from `questionnaire.md` Section 5): (1) direct candidate response to this or a near-identical questionnaire, (2) established third-party candidate questionnaires (Vote411, Ballotpedia Candidate Connection), (3) official statements/voting records, (4) reputable local news coverage, (5) campaign materials.
- One search call per candidate covering all 20 questions — never one call per question (ruled out: 10-20+ minutes per candidate, revisits the rate-limit problem from the earlier parallel-search regression).
- Research is triggered on demand (a button per candidate), never automatically for every candidate in a race.
- Only candidates from the race the voter entered the questionnaire from (`from_office`) can be mapped — not candidates from other races.
- No automated test may make a real network/API call. Mock the Anthropic client, matching the existing pattern in `test_election_lookup.py`.
- Streamlit UI code (`questionnaire_ui.py`, `userinterface.py`) is verified with a manual/headless smoke test, not new pytest coverage — matching the existing project convention (only `election_lookup.py` and `questionnaire_scoring.py` have pytest files today).
- Do not use `use_container_width` (deprecated); this codebase already uses `width="stretch"` where needed — keep that pattern for any new `st.altair_chart` calls (none are added by this plan; existing calls are reused).

---

### Task 1: Candidate research — data models, prompt, parsing, API call

**Files:**
- Modify: `election_lookup.py`
- Modify: `test_election_lookup.py`

**Interfaces:**
- Consumes: `questionnaire_scoring.QUESTIONS` (`list[Question]`, each with `.id`, `.text`, `.approach_1`, `.approach_2`), `questionnaire_scoring.QUESTIONS_BY_ID` (`dict[str, Question]`). Both already exist and are unchanged.
- Produces:
  - `CandidateIssuePosition` dataclass: `question_id: str`, `position: int`, `confidence: Literal["high","medium","low"]`, `source: Source`.
  - `CandidateIssueProfile` dataclass: `candidate_name: str`, `office: Literal["mayor","county","us_house"]`, `positions: dict[str, int]`, `sourced_positions: list[CandidateIssuePosition]`.
  - `parse_candidate_research_response(candidate_name: str, office: str, raw_text: str) -> CandidateIssueProfile`.
  - `research_candidate_positions(zipcode: str, office: str, jurisdiction_name: str, candidate: Candidate, client: "anthropic.Anthropic | None" = None) -> CandidateIssueProfile`.
  - These are consumed by Task 3 (`questionnaire_ui.py`).

- [ ] **Step 1: Write failing tests for response parsing**

Add to `test_election_lookup.py`, near the existing `_valid_single_race_json` / `_office_from_prompt` helpers:

```python
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
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `python3 -m pytest test_election_lookup.py -k candidate_research -v`
Expected: FAIL — `ImportError: cannot import name 'CandidateIssuePosition' from 'election_lookup'` (the names don't exist yet).

- [ ] **Step 3: Add the dataclasses and parsing function**

In `election_lookup.py`, add directly after the existing `LookupResult` dataclass (around line 48, before `_strip_code_fence`):

```python
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
```

Then, directly after the existing `parse_lookup_response` function (around line 107), add:

```python
def parse_candidate_research_response(
    candidate_name: str, office: str, raw_text: str
) -> CandidateIssueProfile:
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc

    if "positions" not in data or not isinstance(data["positions"], list):
        raise ValueError("Model response JSON is missing a 'positions' array")

    from questionnaire_scoring import QUESTIONS_BY_ID

    sourced_positions: list[CandidateIssuePosition] = []
    positions_by_id: dict[str, int] = {}
    for pos_data in data["positions"]:
        question_id = pos_data["question_id"]
        if question_id not in QUESTIONS_BY_ID:
            # Defensively skip an id the model invented rather than failing
            # the whole response over one bad entry.
            continue
        source_data = pos_data["source"]
        position = CandidateIssuePosition(
            question_id=question_id,
            position=pos_data["position"],
            confidence=pos_data["confidence"],
            source=Source(url=source_data["url"], title=source_data.get("title")),
        )
        sourced_positions.append(position)
        positions_by_id[question_id] = position.position

    return CandidateIssueProfile(
        candidate_name=candidate_name,
        office=office,
        positions=positions_by_id,
        sourced_positions=sourced_positions,
    )
```

Note: the `from questionnaire_scoring import QUESTIONS_BY_ID` is placed inside the function body (not at module top) deliberately for this step — Step 5 below moves it to a top-level import once the prompt-building code needs `QUESTIONS` too, so both uses share one import.

- [ ] **Step 4: Run tests, confirm they pass**

Run: `python3 -m pytest test_election_lookup.py -k candidate_research -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Write failing test for the research API call**

Add to `test_election_lookup.py`:

```python
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
```

- [ ] **Step 6: Run tests, confirm they fail**

Run: `python3 -m pytest test_election_lookup.py -k research_candidate_positions -v`
Expected: FAIL — `ImportError: cannot import name 'research_candidate_positions' from 'election_lookup'`.

- [ ] **Step 7: Add the prompt template and `research_candidate_positions`**

In `election_lookup.py`, change the module-level import (around line 8) from:

```python
from typing import Iterator, Literal
```

Keep as-is (no change needed there). Instead, add a new top-level import right after the existing `import anthropic` line (around line 10):

```python
from questionnaire_scoring import QUESTIONS, QUESTIONS_BY_ID
```

Then update `parse_candidate_research_response` (written in Step 3) to remove its local `from questionnaire_scoring import QUESTIONS_BY_ID` line, since it's now imported at module level — the function body's first line becomes `sourced_positions: list[CandidateIssuePosition] = []` immediately after the `if "positions" not in data...` check, with the `QUESTIONS_BY_ID` line deleted.

Next, add this after `OFFICE_DESCRIPTIONS` (around line 120) and before `SINGLE_OFFICE_PROMPT_TEMPLATE`:

```python
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
Race: {office_description} ({jurisdiction_name})
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
```

Finally, add this after `_search_one_office` (around line 194, before `iter_local_elections`):

```python
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
        known_positions_clause=known_positions_clause,
        question_count=len(QUESTIONS),
        questions_block=_format_questions_block(),
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(f"The search for {candidate.name}'s positions was refused.")

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise ValueError(f"Model response for {candidate.name} contained no text output.")

    return parse_candidate_research_response(candidate.name, office, text_blocks[-1])
```

- [ ] **Step 8: Run tests, confirm they pass**

Run: `python3 -m pytest test_election_lookup.py -v`
Expected: PASS — all tests in the file, including the pre-existing ones (confirms no regression from the new top-level `questionnaire_scoring` import).

- [ ] **Step 9: Run the full test suite and commit**

Run: `python3 -m pytest -q`
Expected: PASS, all tests across both test files.

```bash
git add election_lookup.py test_election_lookup.py
git commit -m "$(cat <<'EOF'
Add sourced per-candidate research for the 20 questionnaire questions

research_candidate_positions() runs one search per candidate covering
all 20 questions, recording a position only where real sourced
evidence is found -- never inferred from party or reputation, per
questionnaire.md Section 5.
EOF
)"
```

---

### Task 2: Extend the radar and compass charts to overlay candidates

**Files:**
- Modify: `questionnaire_ui.py`

**Interfaces:**
- Consumes: nothing new from Task 1 (pure charting change, uses only `math`, `pandas`, `altair`, already imported).
- Produces:
  - `_radar_chart(scores_by_category: dict[str, float], candidate_series: list[tuple[str, dict[str, float], str]] | None = None) -> alt.LayerChart` — `candidate_series` items are `(candidate_name, compatibility_by_category, hex_color)`.
  - `_compass_chart(econ_score: float, social_score: float, candidate_points: list[tuple[str, float, float, str]] | None = None) -> alt.LayerChart` — `candidate_points` items are `(candidate_name, econ_score, social_score, hex_color)`.
  - `CANDIDATE_COLORS: list[str]` module constant, consumed by Task 3 to assign a stable color per candidate.
  - Both functions remain backward compatible: called with no third argument, output is equivalent to today's single-series chart.

- [ ] **Step 1: Add the color palette constant**

In `questionnaire_ui.py`, add directly after `CHART_DOMAIN = [-140, 140]` (line 32):

```python
CANDIDATE_COLORS = ["#E45756", "#54A24B", "#F58518", "#B279A2", "#72B7B2"]
```

- [ ] **Step 2: Replace `_radar_chart` to support candidate overlays**

Replace the entire existing `_radar_chart` function (lines 35-72) with:

```python
def _radar_chart(
    scores_by_category: dict[str, float],
    candidate_series: list[tuple[str, dict[str, float], str]] | None = None,
) -> alt.LayerChart:
    categories = list(CATEGORY_LABELS.keys())
    angle_step = 2 * math.pi / len(categories)

    def to_point(series_name: str, category: str, index: int, radius: float) -> dict:
        angle = -math.pi / 2 + index * angle_step
        return {
            "series": series_name,
            "category": CATEGORY_LABELS[category],
            "x": radius * math.cos(angle),
            "y": radius * math.sin(angle),
        }

    voter_points = [
        to_point("Your priorities", category, i, scores_by_category.get(category, 0.0))
        for i, category in enumerate(categories)
    ]
    voter_points.append(voter_points[0])
    voter_df = pd.DataFrame(voter_points)

    all_series = [("Your priorities", scores_by_category, "#4C78A8")] + list(candidate_series or [])
    polygon_rows: list[dict] = []
    for series_name, scores, _color in all_series:
        points = [
            to_point(series_name, category, i, scores.get(category, 0.0))
            for i, category in enumerate(categories)
        ]
        points.append(points[0])
        polygon_rows.extend(points)
    polygon_df = pd.DataFrame(polygon_rows)

    names = [name for name, _scores, _color in all_series]
    colors = [color for _name, _scores, color in all_series]

    label_points = pd.DataFrame([to_point("labels", c, i, 118) for i, c in enumerate(categories)])

    ring_angles = [i * (2 * math.pi / 72) for i in range(73)]
    ring_df = pd.DataFrame(
        [{"x": 100 * math.cos(t), "y": 100 * math.sin(t)} for t in ring_angles]
    )

    x_enc = alt.X("x:Q", axis=None, scale=alt.Scale(domain=CHART_DOMAIN))
    y_enc = alt.Y("y:Q", axis=None, scale=alt.Scale(domain=CHART_DOMAIN))
    color_enc = alt.Color(
        "series:N",
        scale=alt.Scale(domain=names, range=colors),
        legend=alt.Legend(title=None) if candidate_series else None,
    )

    ring = alt.Chart(ring_df).mark_line(color="#cccccc", strokeDash=[2, 2]).encode(x=x_enc, y=y_enc)
    area = alt.Chart(voter_df).mark_area(opacity=0.25, color="#4C78A8").encode(x=x_enc, y=y_enc)
    line = alt.Chart(polygon_df).mark_line().encode(x=x_enc, y=y_enc, color=color_enc)
    points = alt.Chart(polygon_df).mark_point(filled=True).encode(
        x=x_enc, y=y_enc, color=color_enc, tooltip=["series:N", "category:N"]
    )
    labels = alt.Chart(label_points).mark_text(fontSize=11).encode(x=x_enc, y=y_enc, text="category:N")

    return (ring + area + line + points + labels).properties(width=420, height=420)
```

- [ ] **Step 3: Replace `_compass_chart` to support candidate overlays**

Replace the entire existing `_compass_chart` function (lines 75-92) with:

```python
def _compass_chart(
    econ_score: float,
    social_score: float,
    candidate_points: list[tuple[str, float, float, str]] | None = None,
) -> alt.LayerChart:
    rows = [{"series": "You", "econ": econ_score, "social": social_score}]
    colors = ["#E45756"]
    for name, econ, social, color in candidate_points or []:
        rows.append({"series": name, "econ": econ, "social": social})
        colors.append(color)
    point_df = pd.DataFrame(rows)
    names = [row["series"] for row in rows]

    x_enc = alt.X(
        "econ:Q",
        scale=alt.Scale(domain=[-110, 110]),
        title="Economic axis (public investment <-> markets/private)",
    )
    y_enc = alt.Y(
        "social:Q",
        scale=alt.Scale(domain=[-110, 110]),
        title="Social axis (enforcement/centralized <-> civil liberties/decentralized)",
    )
    color_enc = alt.Color(
        "series:N",
        scale=alt.Scale(domain=names, range=colors),
        legend=alt.Legend(title=None) if candidate_points else None,
    )
    hline = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#cccccc").encode(y="y:Q")
    vline = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#cccccc").encode(x="x:Q")
    point = alt.Chart(point_df).mark_point(size=200, filled=True).encode(
        x=x_enc, y=y_enc, color=color_enc, tooltip=["series:N"]
    )
    return (hline + vline + point).properties(width=420, height=420)
```

- [ ] **Step 4: Manual verification — charts still build with no candidates**

Run:

```bash
python3 -c "
from questionnaire_ui import _radar_chart, _compass_chart
chart1 = _radar_chart({'housing': 50.0, 'taxes': 20.0})
chart2 = _compass_chart(10.0, -20.0)
print('radar ok:', chart1 is not None)
print('compass ok:', chart2 is not None)
"
```

Expected: prints `radar ok: True` and `compass ok: True` with no exception (confirms the default no-candidates path still works, since these two calls are exactly how they're invoked today).

- [ ] **Step 5: Manual verification — charts build with candidate overlays**

Run:

```bash
python3 -c "
from questionnaire_ui import _radar_chart, _compass_chart, CANDIDATE_COLORS
series = [('Jane Doe', {'housing': 80.0, 'taxes': 40.0}, CANDIDATE_COLORS[0])]
points = [('Jane Doe', 30.0, -10.0, CANDIDATE_COLORS[0])]
chart1 = _radar_chart({'housing': 50.0, 'taxes': 20.0}, series)
chart2 = _compass_chart(10.0, -20.0, points)
print('radar with candidate ok:', chart1 is not None)
print('compass with candidate ok:', chart2 is not None)
"
```

Expected: prints both `... ok: True` lines with no exception.

- [ ] **Step 6: Commit**

```bash
git add questionnaire_ui.py
git commit -m "$(cat <<'EOF'
Extend radar and compass charts to overlay mapped candidates

Both chart functions accept an optional list of candidate series/
points, rendered in distinct colors with a legend. Called with no
candidates (the existing call sites, unchanged until the next task),
output is equivalent to before this change.
EOF
)"
```

---

### Task 3: Wire up the "Compare with candidates" section

**Files:**
- Modify: `questionnaire_ui.py`
- Modify: `userinterface.py`

**Interfaces:**
- Consumes:
  - From Task 1: `election_lookup.Race`, `election_lookup.Candidate`, `election_lookup.CandidateIssueProfile`, `election_lookup.research_candidate_positions`.
  - From Task 2: `_radar_chart(scores, candidate_series)`, `_compass_chart(econ, social, candidate_points)`, `CANDIDATE_COLORS`.
  - From `questionnaire_scoring.py` (existing, unchanged): `QUESTIONS`, `QUESTIONS_BY_ID`, `compute_candidate_compatibility`.
- Produces: `render_questionnaire(from_office: str | None = None, from_zip: str | None = None, race: Race | None = None) -> None` — the `race` parameter is new; existing callers that omit it keep working (candidate comparison section just shows its "open from a race" message).

- [ ] **Step 1: Update `questionnaire_ui.py` imports**

Change the import block near the top of `questionnaire_ui.py`:

```python
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    compute_compass_scores,
    compute_radar_scores,
)
```

to:

```python
from election_lookup import Race, research_candidate_positions
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    QUESTIONS_BY_ID,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
)
```

- [ ] **Step 2: Add the candidate cache-key helper**

Add directly after the `CANDIDATE_COLORS` constant (added in Task 2, Step 1):

```python
def _candidate_cache_key(zipcode: str, office: str, candidate_name: str) -> tuple[str, str, str]:
    return (zipcode, office, candidate_name)
```

- [ ] **Step 3: Update `render_questionnaire`'s signature and tail**

Change the function signature from:

```python
def render_questionnaire(from_office: str | None = None, from_zip: str | None = None) -> None:
```

to:

```python
def render_questionnaire(
    from_office: str | None = None,
    from_zip: str | None = None,
    race: Race | None = None,
) -> None:
```

Then replace everything from `if "questionnaire_answers" in st.session_state:` through the end of the function (the existing block ending in the `st.info("Candidate compatibility scoring needs...")` call) with:

```python
    if "questionnaire_answers" not in st.session_state:
        return

    st.subheader("Your results")
    radar_scores = compute_radar_scores(st.session_state.questionnaire_importance)
    econ_score, social_score = compute_compass_scores(st.session_state.questionnaire_answers)

    if "candidate_profiles" not in st.session_state:
        st.session_state.candidate_profiles = {}
    if "mapped_candidates" not in st.session_state:
        st.session_state.mapped_candidates = set()

    candidate_series: list[tuple[str, dict[str, float], str]] = []
    candidate_points: list[tuple[str, float, float, str]] = []
    if from_office and from_zip and race:
        for index, candidate in enumerate(race.candidates):
            key = _candidate_cache_key(from_zip, from_office, candidate.name)
            if key not in st.session_state.mapped_candidates:
                continue
            profile = st.session_state.candidate_profiles.get(key)
            if profile is None or not profile.positions:
                continue
            compatibility = compute_candidate_compatibility(
                st.session_state.questionnaire_answers,
                st.session_state.questionnaire_importance,
                profile.positions,
            )
            if compatibility["question_count"] == 0:
                continue
            color = CANDIDATE_COLORS[index % len(CANDIDATE_COLORS)]
            candidate_series.append((candidate.name, compatibility["by_category"], color))
            econ, social = compute_compass_scores(profile.positions)
            candidate_points.append((candidate.name, econ, social, color))

    col_radar, col_compass = st.columns(2)
    with col_radar:
        st.markdown("**What matters most to you**")
        st.altair_chart(_radar_chart(radar_scores, candidate_series), width="stretch")
    with col_compass:
        st.markdown("**Your ideological compass**")
        st.altair_chart(_compass_chart(econ_score, social_score, candidate_points), width="stretch")
        st.caption(
            f"Economic axis: {econ_score:.0f} (negative = more public investment/"
            f"regulation, positive = markets/private development/lower taxation). "
            f"Social axis: {social_score:.0f} (negative = more enforcement/authority/"
            f"centralization, positive = civil liberties/rehabilitation/decentralization)."
        )

    _render_candidate_comparison(from_office, from_zip, race)


def _render_candidate_comparison(
    from_office: str | None, from_zip: str | None, race: Race | None
) -> None:
    st.subheader("Compare with candidates")
    if not (from_office and from_zip and race and race.candidates):
        st.info(
            "Candidate compatibility scoring needs candidates' own answers to these same "
            "20 questions from a verified source (official records, direct questionnaire "
            "responses, or clearly sourced campaign statements) -- not a guess drawn from "
            "general search results. Open this questionnaire from a specific race's "
            "candidates to compare against them."
        )
        return

    for candidate in race.candidates:
        key = _candidate_cache_key(from_zip, from_office, candidate.name)
        profile = st.session_state.candidate_profiles.get(key)
        is_mapped = key in st.session_state.mapped_candidates

        with st.container(border=True):
            header = candidate.name
            if candidate.party:
                header += f" ({candidate.party})"
            st.markdown(f"**{header}**")

            if profile is None:
                if st.button(f"Research and map {candidate.name}", key=f"map_{key}"):
                    with st.status(
                        f"Researching {candidate.name}'s positions on the 20 questions...",
                        expanded=True,
                    ) as status:
                        st.write(
                            "Searching for real, sourced evidence of this candidate's "
                            "position on each question. This commonly takes 30-60 seconds."
                        )
                        try:
                            researched = research_candidate_positions(
                                from_zip, from_office, race.jurisdiction_name, candidate
                            )
                        except Exception as exc:
                            status.update(label="Research failed", state="error")
                            st.error(f"Research failed: {exc}")
                        else:
                            st.session_state.candidate_profiles[key] = researched
                            st.session_state.mapped_candidates.add(key)
                            status.update(label="Research complete", state="complete", expanded=False)
                            st.rerun()
                continue

            coverage = len(profile.sourced_positions)
            if coverage == 0:
                st.write("No sourced positions found for this candidate.")
                continue

            compatibility = compute_candidate_compatibility(
                st.session_state.questionnaire_answers,
                st.session_state.questionnaire_importance,
                profile.positions,
            )

            toggle_label = "Remove from comparison" if is_mapped else f"Add {candidate.name} to comparison"
            if st.button(toggle_label, key=f"toggle_{key}"):
                if is_mapped:
                    st.session_state.mapped_candidates.discard(key)
                else:
                    st.session_state.mapped_candidates.add(key)
                st.rerun()

            if compatibility["overall_pct"] is not None:
                st.write(
                    f"Overall match: {compatibility['overall_pct']:.0f}% "
                    f"(based on {coverage} of {len(QUESTIONS)} questions with sourced evidence)"
                )
            else:
                st.write(
                    f"({coverage} of {len(QUESTIONS)} questions have sourced evidence, but "
                    "none overlap with the questions you answered.)"
                )

            with st.expander(f"Sourced positions for {candidate.name}"):
                for sourced in profile.sourced_positions:
                    question = QUESTIONS_BY_ID[sourced.question_id]
                    badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(sourced.confidence, "⚪")
                    st.write(f"{badge} **{question.text}** _(confidence: {sourced.confidence})_")
                    st.markdown(f"  - [{sourced.source.title or sourced.source.url}]({sourced.source.url})")
```

- [ ] **Step 4: Pass the race into `render_questionnaire` from `userinterface.py`**

In `userinterface.py`, replace the final block:

```python
if st.session_state.get("show_questionnaire"):
    render_questionnaire(
        from_office=st.session_state.get("questionnaire_from_office"),
        from_zip=st.session_state.get("questionnaire_from_zip"),
    )
```

with:

```python
if st.session_state.get("show_questionnaire"):
    from_office = st.session_state.get("questionnaire_from_office")
    from_zip = st.session_state.get("questionnaire_from_zip")
    race = None
    if from_zip and from_zip in st.session_state.lookup_cache:
        by_office = {r.office: r for r in st.session_state.lookup_cache[from_zip].races}
        race = by_office.get(from_office)
    render_questionnaire(from_office=from_office, from_zip=from_zip, race=race)
```

- [ ] **Step 5: Compile-check both files**

Run: `python3 -m py_compile questionnaire_ui.py userinterface.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Run the full pytest suite**

Run: `python3 -m pytest -q`
Expected: PASS, all existing tests (this task adds no new pytest tests — `questionnaire_ui.py`/`userinterface.py` are verified by the manual smoke test in Step 7, matching the existing project convention that Streamlit UI files aren't pytest-covered).

- [ ] **Step 7: Manual smoke test with a mocked Anthropic client**

Create a throwaway harness at the repo root, `_smoke_candidate_mapping.py` (leading underscore, not committed — running `streamlit run` from the repo root puts the repo root on `sys.path` automatically, so this needs no path setup to import `election_lookup` or exec `userinterface.py`):

```python
import os
from unittest.mock import MagicMock

os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

import election_lookup

RACE_JSON = """{"races": [{"office": "mayor", "jurisdiction_name": "Springfield",
    "election_date": "2026-11-03", "election_type": "general", "notes": null,
    "candidates": [{"name": "Jane Doe", "party": "Independent", "incumbent": true,
    "positions": [{"summary": "Supports expanding the downtown bus line.",
    "confidence": "high", "sources": [{"url": "https://example.com/jane", "title": "Platform"}]}]}]}]}"""

CANDIDATE_JSON = """{"positions": [
    {"question_id": "housing_zoning_density", "position": 4, "confidence": "high",
     "source": {"url": "https://example.com/vote411", "title": "Vote411 guide"}},
    {"question_id": "taxes_shortfall", "position": 2, "confidence": "medium",
     "source": {"url": "https://example.com/news", "title": null}}
]}"""


def _fake_create(*args, **kwargs):
    content = kwargs["messages"][0]["content"]
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = CANDIDATE_JSON if "housing_zoning_density" in content else RACE_JSON
    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"
    return response


class _FakeAnthropic:
    def __init__(self, *a, **kw):
        self.messages = MagicMock()
        self.messages.create.side_effect = _fake_create


election_lookup.anthropic.Anthropic = _FakeAnthropic

exec(open("userinterface.py").read())
```

Then, from the repo root:

```bash
streamlit run _smoke_candidate_mapping.py --server.headless true --server.port 8599 &
sleep 4
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8599
```

Expected: `200`, and no traceback in the terminal running Streamlit.

Then, in a browser at `http://localhost:8599`: enter zip `62704`, click "Find my elections", wait for the mayoral race to appear, click "Take the issues questionnaire", answer the form (defaults are fine), click "See my results", confirm the radar/compass render, then in the new "Compare with candidates" section click "Research and map Jane Doe" and confirm: a status spinner appears, then "Jane Doe" appears as a second color on both charts, an overall match % with "(based on 2 of 20 questions...)" is shown, and the "Sourced positions for Jane Doe" expander lists both questions with working source links. Click "Remove from comparison" and confirm Jane Doe disappears from both charts without needing to re-research.

Stop the server and remove the harness: `pkill -f "streamlit run.*8599"; rm _smoke_candidate_mapping.py`.

- [ ] **Step 8: Commit**

```bash
git add questionnaire_ui.py userinterface.py
git commit -m "$(cat <<'EOF'
Add on-demand candidate research and comparison to the questionnaire

Voters can research a specific candidate from the race they entered
the questionnaire from; a real sourced search populates their answers
to the 20 questions, which then overlay the voter's own radar/compass
charts and show a category-by-category compatibility breakdown with
links to every source used.
EOF
)"
```

---

## Post-implementation check

After all three tasks: run `python3 -m pytest -q` once more (expect full pass), then re-read the design spec at `docs/superpowers/specs/2026-07-25-candidate-compass-mapping-design.md` section by section and confirm each requirement has a corresponding change:
- Sourced research per candidate → Task 1.
- On-demand trigger, scoped to the entered race → Task 3, Step 3.
- Compass + radar overlay → Task 2 + Task 3.
- Coverage transparency ("N of 20 questions") and sourced-evidence display → Task 3, Step 3.
- Multiple candidates mappable at once → Task 3, Step 3 (loop over `race.candidates`, independent toggle state per candidate).
