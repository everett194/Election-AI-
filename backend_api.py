"""
backend_api.py

JSON API for the ElectMatch frontend (frontend/). Wraps election_lookup.py
and questionnaire_scoring.py directly -- no logic is duplicated here, this
module only adapts existing functions to HTTP request/response shapes.

Run with:
    uvicorn backend_api:app --reload --port 8000

Requires the same two API keys as streamlitrun.py (never sent to the
frontend -- see tavily_search.py and election_lookup.py for where they're
actually used):
    export ANTHROPIC_API_KEY=sk-ant-...
    export TAVILY_API_KEY=tvly-...
"""

from __future__ import annotations

import os
import re
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import answer_storage
import election_lookup
from election_lookup import Candidate as BackendCandidate
from questionnaire_scoring import (
    CATEGORY_LABELS,
    QUESTIONS,
    compute_candidate_compatibility,
    compute_compass_scores,
    compute_radar_scores,
    derive_candidate_weights,
)

app = FastAPI(title="ElectMatch API")

_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8443,http://127.0.0.1:8443"
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", _default_origins).split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ZIP_PATTERN = re.compile(r"^\d{5}$")
OFFICE_LABELS = {"mayor": "Mayoral", "county": "County", "us_house": "U.S. House"}


def _missing_key_message(exc: RuntimeError) -> str:
    # RuntimeError messages from election_lookup.py / tavily_search.py name the
    # missing env var but never the key value itself -- safe to pass through.
    return str(exc)


# --- Serialization helpers ------------------------------------------------


def _source_to_dict(source: "election_lookup.Source | None") -> dict | None:
    if source is None:
        return None
    return {"url": source.url, "title": source.title}


def _position_to_dict(position: "election_lookup.Position") -> dict:
    return {
        "summary": position.summary,
        "confidence": position.confidence,
        "sources": [_source_to_dict(s) for s in position.sources],
    }


def _candidate_to_dict(candidate: BackendCandidate) -> dict:
    return {
        "name": candidate.name,
        "party": candidate.party,
        "incumbent": candidate.incumbent,
        "positions": [_position_to_dict(p) for p in candidate.positions],
    }


def _race_to_dict(race: "election_lookup.Race") -> dict:
    return {
        "office": race.office,
        "office_label": OFFICE_LABELS.get(race.office, race.office),
        "jurisdiction_name": race.jurisdiction_name,
        "election_date": race.election_date,
        "election_type": race.election_type,
        "notes": race.notes,
        "candidates": [_candidate_to_dict(c) for c in race.candidates],
    }


def _question_to_dict(question) -> dict:
    return {
        "id": question.id,
        "category": question.category,
        "category_label": CATEGORY_LABELS[question.category],
        "econ_weight": question.econ_weight,
        "social_weight": question.social_weight,
        "text": question.text,
        "position_1": question.position_1,
        "position_2": question.position_2,
        "selection_priority": question.selection_priority,
        "research_terms": list(question.research_terms),
    }


def _issue_position_to_dict(pos: "election_lookup.CandidateIssuePosition") -> dict:
    return {
        "question_id": pos.question_id,
        "position": pos.position,
        "confidence": pos.confidence,
        "source": _source_to_dict(pos.source),
    }


def _profile_to_dict(profile: "election_lookup.CandidateIssueProfile") -> dict:
    econ, social = compute_compass_scores(profile.positions)
    has_econ, has_social = profile.covered_axes()
    sourced_count = sum(1 for p in profile.sourced_positions if p.confidence != "speculative")
    return {
        "candidate_name": profile.candidate_name,
        "office": profile.office,
        "positions": profile.positions,
        "sourced_positions": [_issue_position_to_dict(p) for p in profile.sourced_positions],
        "coverage": {
            "total_questions": len(QUESTIONS),
            "answered": len(profile.positions),
            "sourced": sourced_count,
            "speculative": len(profile.sourced_positions) - sourced_count,
        },
        "categories_covered": sorted(profile.covered_categories()),
        "compass": {"econ": econ, "social": social, "has_econ": has_econ, "has_social": has_social},
        "emphasis": profile.emphasis,
    }


# --- GET /api/health -------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# --- GET /api/questions -----------------------------------------------------


@app.get("/api/questions")
def get_questions() -> list[dict]:
    return [_question_to_dict(q) for q in QUESTIONS]


# --- GET /api/elections?zip=XXXXX -------------------------------------------


@app.get("/api/elections")
def get_elections(zip: str) -> dict:
    zipcode = zip.strip()
    if not ZIP_PATTERN.match(zipcode):
        raise HTTPException(status_code=400, detail="Please provide a valid 5-digit US zip code.")

    try:
        result = election_lookup.find_local_elections_via_tavily(zipcode)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=_missing_key_message(exc)) from exc
    except Exception as exc:  # search/parsing failure -- surface, don't crash
        raise HTTPException(status_code=502, detail=f"Election search failed: {exc}") from exc

    return {
        "zipcode": result.zipcode,
        "retrieved_at": result.retrieved_at,
        "races": [_race_to_dict(r) for r in result.races],
    }


# --- POST /api/candidates/research ------------------------------------------


class CandidateInput(BaseModel):
    name: str
    party: str | None = None
    incumbent: bool | None = None


class CandidateResearchRequest(BaseModel):
    zipcode: str
    office: str
    jurisdiction_name: str
    candidates: list[CandidateInput]
    # Voter's ranked priority categories, if chosen already -- optional so
    # existing callers (e.g. the background research kicked off right after
    # an election search, before the voter has answered anything) keep
    # working unchanged. See election_lookup.research_candidates_for_race_with_fallback.
    ranked_categories: list[str] | None = None


@app.post("/api/candidates/research")
def research_candidates(body: CandidateResearchRequest) -> dict:
    if not body.candidates:
        raise HTTPException(status_code=400, detail="At least one candidate is required.")
    if body.office not in election_lookup.OFFICES:
        raise HTTPException(status_code=400, detail=f"Unknown office '{body.office}'.")

    candidates = [
        BackendCandidate(name=c.name, party=c.party, incumbent=c.incumbent) for c in body.candidates
    ]

    try:
        profiles = election_lookup.research_candidates_for_race_with_fallback(
            body.zipcode,
            body.office,
            body.jurisdiction_name,
            candidates,
            selected_categories=body.ranked_categories,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=_missing_key_message(exc)) from exc
    except Exception as exc:  # research/parsing failure -- surface, don't crash
        raise HTTPException(status_code=502, detail=f"Candidate research failed: {exc}") from exc

    return {"profiles": {name: _profile_to_dict(profile) for name, profile in profiles.items()}}


# --- POST /api/results -------------------------------------------------------


class CandidateResultInput(BaseModel):
    name: str
    office: str
    positions: dict[str, int]
    emphasis: dict[str, Annotated[int, Field(ge=1, le=5)]] = {}


class ResultsRequest(BaseModel):
    answers: dict[str, int]
    # The voter's ranked (1st-4th) priority category ids from Stage 1 of the
    # questionnaire, index 0 = rank 1. Effective per-candidate compatibility
    # weight is derived from this plus each candidate's own emphasis
    # server-side (see derive_candidate_weights) -- the frontend never sends
    # a weight or importance number directly.
    ranked_categories: list[str] = []
    candidates: list[CandidateResultInput] = []


@app.post("/api/results")
def get_results(body: ResultsRequest) -> dict:
    answer_storage.save_submission(body.answers, body.ranked_categories)

    radar = compute_radar_scores(body.ranked_categories, body.answers.keys())
    voter_econ, voter_social = compute_compass_scores(body.answers)

    candidate_results = []
    for candidate in body.candidates:
        weights = derive_candidate_weights(body.ranked_categories, body.answers.keys(), candidate.emphasis)
        compatibility = compute_candidate_compatibility(body.answers, weights, candidate.positions)
        has_any_position = bool(candidate.positions)
        econ = social = None
        if has_any_position:
            econ, social = compute_compass_scores(candidate.positions)
        candidate_results.append(
            {
                "name": candidate.name,
                "office": candidate.office,
                "compass": {"econ": econ, "social": social} if has_any_position else None,
                "compatibility": compatibility,
            }
        )

    # Rank by overall_pct descending; candidates with no qualifying questions
    # (overall_pct is None) sort last rather than being excluded outright.
    candidate_results.sort(
        key=lambda r: (r["compatibility"]["overall_pct"] is None, -(r["compatibility"]["overall_pct"] or 0))
    )

    return {
        "radar": radar,
        "voter_compass": {"econ": voter_econ, "social": voter_social},
        "candidates": candidate_results,
    }
