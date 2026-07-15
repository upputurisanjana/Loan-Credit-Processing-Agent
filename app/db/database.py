"""
app/db/database.py — append-only audit persistence.

Rules enforced here
-------------------
1. INSERT into decision_records is the ONLY write path for new records.
2. The ONLY UPDATE allowed on decision_records is recording the human
   gate decision (human_decision, human_reviewer, override_reason,
   decided_at) — and only when human_decision is currently NULL.
3. The approved_notice_text column may be updated independently by the
   reviewer via the /notice endpoint (before or after human_decision is set).
4. The awaiting_info_items column may be updated when reviewer requests info.
5. No DELETE statement touches decision_records or decision_amendments.
6. Corrections always go to decision_amendments as a new linked row.

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
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.decision import DecisionRecord, DecisionAmendment

log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# ---------------------------------------------------------------------------
# Connection cache — one connection per process, protected by a lock.
# sqlite3 connections are not thread-safe by themselves; the lock serialises
# all writes so concurrent FastAPI workers don't race on the same connection.
# ---------------------------------------------------------------------------
_db_connection: Optional[sqlite3.Connection] = None
_db_lock = threading.Lock()


def get_db(db_url: Optional[str] = None) -> sqlite3.Connection:
    """
    Return the cached sqlite3 connection to the audit database.

    Opens and initialises the connection on first call, then returns the
    same object on every subsequent call (singleton per process).

    All callers share one connection; the module-level _db_lock must be
    held for any write operation — see insert_decision, record_human_decision
    etc., which acquire the lock internally.

    The DATABASE_URL env var is expected to be in the form
    "sqlite:///./path/to/audit.db" (SQLAlchemy convention) or just a
    plain file path.  Defaults to ./audit.db if not set.
    """
    global _db_connection  # noqa: PLW0603
    if _db_connection is not None:
        return _db_connection

    with _db_lock:
        # Double-checked locking: another thread may have initialised while
        # we waited for the lock.
        if _db_connection is not None:
            return _db_connection

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
        # WAL mode allows concurrent reads while a write is in progress,
        # reducing lock contention under light multi-worker load.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_schema(conn)
        _migrate_schema(conn)

        _db_connection = conn
        log.info("db: opened connection to %s (WAL mode)", path)
        return _db_connection


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """
    Apply additive migrations to existing databases.
    Each ALTER TABLE is wrapped in a try/except so it is a no-op if the
    column already exists (SQLite does not support IF NOT EXISTS for columns).
    """
    migrations = [
        "ALTER TABLE decision_records ADD COLUMN applicant_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE decision_records ADD COLUMN applicant_address TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE decision_records ADD COLUMN loan_amount_requested REAL NOT NULL DEFAULT 0.0",
        "ALTER TABLE decision_records ADD COLUMN applicant_notes TEXT",
        "ALTER TABLE decision_records ADD COLUMN approved_notice_text TEXT",
        "ALTER TABLE decision_records ADD COLUMN awaiting_info_items TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE decision_records ADD COLUMN pipeline_trace TEXT NOT NULL DEFAULT '[]'",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists — skip silently
            pass


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
            applicant_name,
            applicant_address,
            loan_amount_requested,
            applicant_notes,
            score_breakdown_json,
            fairness_match,
            fairness_original_band,
            fairness_masked_band,
            fairness_original_composite,
            fairness_masked_composite,
            agent_recommendation,
            rationale,
            adverse_action_draft,
            approved_notice_text,
            human_decision,
            human_reviewer,
            override_reason,
            decided_at,
            awaiting_info_items,
            pipeline_trace,
            created_at,
            immutable
        ) VALUES (
            :application_id,
            :policy_version,
            :applicant_name,
            :applicant_address,
            :loan_amount_requested,
            :applicant_notes,
            :score_breakdown_json,
            :fairness_match,
            :fairness_original_band,
            :fairness_masked_band,
            :fairness_original_composite,
            :fairness_masked_composite,
            :agent_recommendation,
            :rationale,
            :adverse_action_draft,
            :approved_notice_text,
            :human_decision,
            :human_reviewer,
            :override_reason,
            :decided_at,
            :awaiting_info_items,
            :pipeline_trace,
            :created_at,
            1
        )
    """
    params = {
        "application_id": record.application_id,
        "policy_version": record.policy_version,
        "applicant_name": record.applicant_name,
        "applicant_address": record.applicant_address,
        "loan_amount_requested": record.loan_amount_requested,
        "applicant_notes": record.applicant_notes,
        "score_breakdown_json": record.score_breakdown.model_dump_json(),
        "fairness_match": int(record.fairness_check.match),
        "fairness_original_band": record.fairness_check.original_band,
        "fairness_masked_band": record.fairness_check.masked_band,
        "fairness_original_composite": record.fairness_check.original_composite,
        "fairness_masked_composite": record.fairness_check.masked_composite,
        "agent_recommendation": record.agent_recommendation,
        "rationale": record.rationale,
        "adverse_action_draft": record.adverse_action_draft,
        "approved_notice_text": record.approved_notice_text,
        "human_decision": record.human_decision,
        "human_reviewer": record.human_reviewer,
        "override_reason": record.override_reason,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "awaiting_info_items": json.dumps(record.awaiting_info_items),
        "pipeline_trace": json.dumps(record.pipeline_trace),
        "created_at": record.created_at.isoformat(),
    }
    try:
        with _db_lock:
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
    The ONLY UPDATE allowed on decision_records for the human gate.

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
    with _db_lock:
        cursor = conn.execute(sql, {
            "application_id": application_id,
            "human_decision": human_decision,
            "human_reviewer": human_reviewer,
            "override_reason": override_reason,
            "decided_at": datetime.now(timezone.utc).isoformat(),
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


def update_approved_notice(
    conn: sqlite3.Connection,
    application_id: str,
    approved_notice_text: str,
) -> None:
    """
    Store the reviewer-approved version of the adverse action notice.
    May be called before or after the human_decision is recorded.
    """
    sql = """
        UPDATE decision_records
        SET approved_notice_text = :notice_text
        WHERE application_id = :application_id
    """
    with _db_lock:
        cursor = conn.execute(sql, {
            "application_id": application_id,
            "notice_text": approved_notice_text,
        })
        conn.commit()
    if cursor.rowcount == 0:
        raise ValueError(f"Application {application_id!r} not found.")
    log.info("db: approved_notice_text updated for app_id=%s", application_id)


def update_awaiting_info(
    conn: sqlite3.Connection,
    application_id: str,
    items: list[str],
) -> None:
    """
    Store the list of items the reviewer has requested from the applicant.
    Clears awaiting_info_items when called with an empty list (i.e. when
    the applicant has responded and the reviewer resumes review).
    """
    sql = """
        UPDATE decision_records
        SET awaiting_info_items = :items_json
        WHERE application_id = :application_id
          AND human_decision IS NULL
    """
    with _db_lock:
        cursor = conn.execute(sql, {
            "application_id": application_id,
            "items_json": json.dumps(items),
        })
        conn.commit()
    if cursor.rowcount == 0:
        raise ValueError(
            f"Cannot update awaiting_info for {application_id!r}: "
            "record not found or already decided."
        )
    log.info("db: awaiting_info_items updated for app_id=%s (%d items)", application_id, len(items))


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
    with _db_lock:
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


def fetch_all_decisions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all decision_records rows, oldest first."""
    return conn.execute(
        "SELECT * FROM decision_records ORDER BY created_at ASC"
    ).fetchall()


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
