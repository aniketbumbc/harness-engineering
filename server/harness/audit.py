from psycopg.types.json import Jsonb

from .db import get_conn


def log_event(case_id: str, node: str, event: str, detail: dict | None = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO harness.audit_events (case_id, node, event, detail) "
            "VALUES (%s, %s, %s, %s)",
            (case_id, node, event, Jsonb(detail or {})),
        )