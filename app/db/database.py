"""
app/db/database.py — append-only audit persistence.

Rules enforced here
-------------------
1. INSERT into decision_records is the ONLY write path for new records.
2. The ONLY UPDATE allowed on decision_records is recording the human
   gate decision (human_decision, human_reviewer, override_reason,
   decided_at) — and only when human_decision is currently NULL.
3. No DELETE statement touches decision_records or decision_amendments.
4. Corrections always go to decision_amendments as a new linked row.

Usage
-----
    from app.db.database import get_db, insert_decision, record_human_decision

    db = get_db()
    insert_decision(db, record)
    record_human_decision(db, app_id, "approve", "underwriter_1", None)
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.decision import DecisionRecord, DecisionAmendment

log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def get_db(db_url: Optional[str] = None) -> sqlite3.Connection:
    """
    Return a sqlite3 connection to the audit database.

    The DATABASE_URL env var is expected to be in the form
    "sqlite:///./path/to/audit.db" (SQLAlchemy convention) or just a
    plain file path.  Defaults to ./audit.db if not set.
    """
    raw_url = db_url or os.environ.get("DATABASE_URL", "sqlite:///./audit.db")

    # Strip SQLAlchemy prefix if present
    if raw_url.startswith("sqlite:///"):
        path = raw_url[len("sqlite:///"):]
    else:
        path = raw_url

    # Ensure parent directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def insert_decision(conn: sqlite3.Connection, record: DecisionRecord) -> None:
    """
    INSERT a new DecisionRecord into decision_records.

    This is append-only — raises if application_id already exists.
    The score_breakdown is serialised to JSON for storage; all other
    structured fields are stored in dedicated columns for queryability.
    """
    sql = """
        INSERT INTO decision_records (
            application_id,
            policy_version,
            score_breakdown_json,
            fairness_match,
            fairness_original_band,
            fairness_masked_band,
            fairness_original_composite,
            fairness_masked_composite,
            agent_recommendation,
            rationale,
            adverse_action_draft,
            human_decision,
            human_reviewer,
            override_reason,
            decided_at,
            created_at,
            immutable
        ) VALUES (
            :application_id,
            :policy_version,
            :score_breakdown_json,
            :fairness_match,
            :fairness_original_band,
            :fairness_masked_band,
            :fairness_original_composite,
            :fairness_masked_composite,
            :agent_recommendation,
            :rationale,
            :adverse_action_draft,
            :human_decision,
            :human_reviewer,
            :override_reason,
            :decided_at,
            :created_at,
            1
        )
    """
    params = {
        "application_id": record.application_id,
        "policy_version": record.policy_version,
        "score_breakdown_json": record.score_breakdown.model_dump_json(),
        "fairness_match": int(record.fairness_check.match),
        "fairness_original_band": record.fairness_check.original_band,
        "fairness_masked_band": record.fairness_check.masked_band,
        "fairness_original_composite": record.fairness_check.original_composite,
        "fairness_masked_composite": record.fairness_check.masked_composite,
        "agent_recommendation": record.agent_recommendation,
        "rationale": record.rationale,
        "adverse_action_draft": record.adverse_action_draft,
        "human_decision": record.human_decision,
        "human_reviewer": record.human_reviewer,
        "override_reason": record.override_reason,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "created_at": record.created_at.isoformat(),
    }
    try:
        conn.execute(sql, params)
        conn.commit()
        log.info("db: inserted decision_record app_id=%s", record.application_id)
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            f"decision_record for {record.application_id!r} already exists "
            "(append-only: use insert_amendment for corrections)"
        ) from exc


def record_human_decision(
    conn: sqlite3.Connection,
    application_id: str,
    human_decision: str,
    human_reviewer: str,
    override_reason: Optional[str],
) -> None:
    """
    The ONLY UPDATE allowed on decision_records.

    Updates human_decision, human_reviewer, override_reason, decided_at
    when the underwriter acts at the human gate.  Only runs if
    human_decision is currently NULL (prevents re-deciding a closed case).
    """
    sql = """
        UPDATE decision_records
        SET
            human_decision  = :human_decision,
            human_reviewer  = :human_reviewer,
            override_reason = :override_reason,
            decided_at      = :decided_at
        WHERE application_id = :application_id
          AND human_decision IS NULL
    """
    cursor = conn.execute(sql, {
        "application_id": application_id,
        "human_decision": human_decision,
        "human_reviewer": human_reviewer,
        "override_reason": override_reason,
        "decided_at": datetime.utcnow().isoformat(),
    })
    conn.commit()

    if cursor.rowcount == 0:
        raise ValueError(
            f"Cannot update human decision for {application_id!r}: "
            "record not found or already decided."
        )
    log.info(
        "db: human_decision recorded app_id=%s decision=%s reviewer=%s",
        application_id, human_decision, human_reviewer,
    )


def insert_amendment(conn: sqlite3.Connection, amendment: DecisionAmendment) -> None:
    """
    Append a correction record to decision_amendments.
    The original decision_records row is NEVER touched.
    """
    sql = """
        INSERT INTO decision_amendments (
            amendment_id,
            original_application_id,
            amended_by,
            amendment_reason,
            field_changes_json,
            amended_at
        ) VALUES (
            :amendment_id,
            :original_application_id,
            :amended_by,
            :amendment_reason,
            :field_changes_json,
            :amended_at
        )
    """
    conn.execute(sql, {
        "amendment_id": amendment.amendment_id,
        "original_application_id": amendment.original_application_id,
        "amended_by": amendment.amended_by,
        "amendment_reason": amendment.amendment_reason,
        "field_changes_json": json.dumps(amendment.field_changes),
        "amended_at": amendment.amended_at.isoformat(),
    })
    conn.commit()
    log.info(
        "db: inserted amendment amendment_id=%s original_app_id=%s",
        amendment.amendment_id, amendment.original_application_id,
    )


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def fetch_decision(
    conn: sqlite3.Connection,
    application_id: str,
) -> Optional[sqlite3.Row]:
    """Return the decision_records row for application_id, or None."""
    row = conn.execute(
        "SELECT * FROM decision_records WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    return row


def fetch_amendments(
    conn: sqlite3.Connection,
    application_id: str,
) -> list[sqlite3.Row]:
    """Return all amendments for a given application_id."""
    rows = conn.execute(
        "SELECT * FROM decision_amendments WHERE original_application_id = ? ORDER BY amended_at",
        (application_id,),
    ).fetchall()
    return rows
