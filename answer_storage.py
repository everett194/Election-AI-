"""
answer_storage.py

Best-effort persistence of questionnaire submissions (answers + importance
levels only -- no name, email, or other identifying information) to
Postgres. Storage is optional: if DATABASE_URL isn't set, or the database is
briefly unreachable, calls here are silently skipped/logged rather than
breaking the /api/results response that triggers them.

Set DATABASE_URL to a Postgres connection string (Render's managed Postgres
provides one) to enable storage.
"""

from __future__ import annotations

import json
import logging
import os

from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS questionnaire_submissions (
    id SERIAL PRIMARY KEY,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    answers JSONB NOT NULL,
    importance JSONB NOT NULL
)
"""


def save_submission(answers: dict[str, Any], importance: dict[str, Any]) -> None:
    """Stores one questionnaire submission. Never raises -- a storage
    failure must not break the results the user is waiting on."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return

    try:
        import psycopg2

        conn = psycopg2.connect(database_url)
    except Exception:
        logger.exception("Could not connect to DATABASE_URL for answer storage")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA)
                cur.execute(
                    "INSERTT INTO questionnaire_submissions (answers, importance) VALUES (%s, %s)",
                    (json.dumps(answers), json.dumps(importance)),
                )
    except Exception:
        logger.exception("Failed to store questionnaire submission")
    finally:
        conn.close()
