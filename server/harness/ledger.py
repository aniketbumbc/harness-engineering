from psycopg.types.json import Jsonb

from .db import get_conn


def get(case_id: str, action: str) -> dict | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM harness.action_ledger WHERE case_id=%s AND action=%s",
            (case_id, action),
        ).fetchone()


def begin(case_id: str, action: str, request: dict) -> dict:
    """Create the row as 'pending' (once), count the attempt, return the row."""
    key = f"{case_id}:{action}"          # this is the idempotency key
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO harness.action_ledger
               (case_id, action, idempotency_key, status, request)
               VALUES (%s, %s, %s, 'pending', %s)
               ON CONFLICT (case_id, action) DO NOTHING""",
            (case_id, action, key, Jsonb(request)),
        )
        return conn.execute(
            """UPDATE harness.action_ledger
               SET attempts = attempts + 1, status = 'pending', updated_at = now()
               WHERE case_id=%s AND action=%s AND status <> 'done'
               RETURNING *""",
            (case_id, action),
        ).fetchone()


def mark_done(case_id: str, action: str, response: dict):
    with get_conn() as conn:
        conn.execute(
            """UPDATE harness.action_ledger
               SET status='done', response=%s, error=NULL, updated_at=now()
               WHERE case_id=%s AND action=%s""",
            (Jsonb(response, dumps=__import__("json").dumps), case_id, action),
        )


def mark_failed(case_id: str, action: str, error: str):
    with get_conn() as conn:
        conn.execute(
            """UPDATE harness.action_ledger
               SET status='failed', error=%s, updated_at=now()
               WHERE case_id=%s AND action=%s""",
            (error, case_id, action),
        )