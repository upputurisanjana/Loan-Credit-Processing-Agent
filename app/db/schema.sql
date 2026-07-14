-- app/db/schema.sql
-- Append-only audit store for credit decisioning records.
--
-- Design rules (enforced at the application layer in database.py):
--   1. No UPDATE or DELETE statements ever touch decision_records.
--   2. Corrections are written as a new row in decision_amendments that
--      references the original application_id — the original is never mutated.
--   3. The immutable column is a documentary marker; enforcement is in code.

-- ──────────────────────────────────────────────────────────────────────────
-- decision_records
-- One row per application pipeline run.  Written once at HUMAN_GATE entry;
-- human_decision / human_reviewer / override_reason / decided_at are updated
-- by the single allowed UPDATE (see database.py: record_human_decision).
-- All other fields are immutable after initial insert.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decision_records (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id          TEXT    NOT NULL UNIQUE,
    policy_version          TEXT    NOT NULL,

    -- Applicant details (captured at intake, surfaced to reviewers)
    applicant_name          TEXT    NOT NULL DEFAULT '',
    applicant_address       TEXT    NOT NULL DEFAULT '',
    loan_amount_requested   REAL    NOT NULL DEFAULT 0.0,
    applicant_notes         TEXT,               -- NULL if applicant left blank

    -- Score breakdown (stored as JSON blob for portability)
    score_breakdown_json    TEXT    NOT NULL,

    -- Fairness check result
    fairness_match          INTEGER NOT NULL,   -- 0 = mismatch (flag), 1 = match
    fairness_original_band  TEXT    NOT NULL,
    fairness_masked_band    TEXT    NOT NULL,
    fairness_original_composite REAL NOT NULL,
    fairness_masked_composite   REAL NOT NULL,

    -- Agent outputs (immutable after insert)
    agent_recommendation    TEXT    NOT NULL,   -- approve | refer | decline
    rationale               TEXT    NOT NULL,
    adverse_action_draft    TEXT,               -- NULL unless DECLINE path

    -- Reviewer-approved notice text (after editing in NoticeEditor)
    approved_notice_text    TEXT,               -- NULL until reviewer approves

    -- Human gate (nullable until underwriter acts — the only allowed update)
    human_decision          TEXT,               -- approve | refer | decline | NULL
    human_reviewer          TEXT,
    override_reason         TEXT,               -- required when overriding
    decided_at              TEXT,               -- ISO-8601

    -- Request-more-information items (JSON list of strings)
    awaiting_info_items     TEXT    NOT NULL DEFAULT '[]',

    -- Metadata
    created_at              TEXT    NOT NULL,   -- ISO-8601, set at insert
    immutable               INTEGER NOT NULL DEFAULT 1
);

-- ──────────────────────────────────────────────────────────────────────────
-- decision_amendments
-- Post-hoc corrections linked to an existing decision_records row.
-- The original row is NEVER modified; amendments are a new linked row.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decision_amendments (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    amendment_id            TEXT    NOT NULL UNIQUE,
    original_application_id TEXT    NOT NULL
                            REFERENCES decision_records(application_id),
    amended_by              TEXT    NOT NULL,
    amendment_reason        TEXT    NOT NULL,
    field_changes_json      TEXT    NOT NULL,   -- JSON object of key→new_value
    amended_at              TEXT    NOT NULL    -- ISO-8601
);

-- Index for fast lookup by application_id
CREATE INDEX IF NOT EXISTS idx_decision_records_app_id
    ON decision_records (application_id);

CREATE INDEX IF NOT EXISTS idx_amendments_app_id
    ON decision_amendments (original_application_id);
