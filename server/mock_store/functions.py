import time
import uuid

from fastapi import HTTPException

from . import seed
from .db import get_conn

FAILURES: dict[str, dict] = {}
TARGETS = {"orders", "tracking", "payments", "refund", "email", "tickets"}


def maybe_fail(target: str):
    failure = FAILURES.get(target)
    if not failure or failure["remaining"] <= 0:
        return
    failure["remaining"] -= 1
    if failure["mode"] == "timeout":
        time.sleep(failure["delay"])
        raise HTTPException(504, f"{target} timed out (injected)")
    raise HTTPException(503, f"{target} unavailable (injected)")


def set_failure(target: str, mode: str, count: int, delay: int):
    if target not in TARGETS or mode not in {"error", "timeout"}:
        raise HTTPException(422, f"target must be one of {sorted(TARGETS)}; mode error|timeout")
    FAILURES[target] = {"mode": mode, "remaining": count, "delay": delay}
    return FAILURES


def get_failures():
    return FAILURES


def clear_failures():
    FAILURES.clear()
    return {"cleared": True}


def reset_store():
    seed.run()
    FAILURES.clear()
    return {"reset": True}


def list_refunds():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM store.refunds ORDER BY created_at").fetchall()


def list_emails():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM store.emails ORDER BY id").fetchall()


def check_health():
    with get_conn() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "service": "mock_store"}


def get_order(order_id: str):
    maybe_fail("orders")
    with get_conn() as conn:
        row = conn.execute(
            """SELECT o.*, c.name AS customer_name, c.email AS customer_email
               FROM store.orders o JOIN store.customers c USING (customer_id)
               WHERE o.order_id = %s""",
            (order_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "order not found")
    return row


def get_tracking(order_id: str):
    maybe_fail("tracking")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT event, location, occurred_at FROM store.tracking "
            "WHERE order_id = %s ORDER BY occurred_at",
            (order_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(404, "no tracking for order")
    return {"order_id": order_id, "events": rows}


def get_payments(order_id: str):
    maybe_fail("payments")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM store.payments WHERE order_id = %s ORDER BY charged_at",
            (order_id,),
        ).fetchall()
    return {"order_id": order_id, "payments": rows}


def customer_refunds(customer_id: str, days: int = 90):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM store.refunds
               WHERE customer_id = %s AND created_at >= now() - make_interval(days => %s)
               ORDER BY created_at DESC""",
            (customer_id, days),
        ).fetchall()
    return {"customer_id": customer_id, "window_days": days, "count": len(rows), "refunds": rows}


def create_refund(order_id: str, amount, reason: str, idempotency_key: str):
    maybe_fail("refund")
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM store.refunds WHERE idempotency_key = %s", (idempotency_key,)
        ).fetchone()
        if existing:
            return {**existing, "created": False}

        order = conn.execute(
            "SELECT customer_id FROM store.orders WHERE order_id = %s", (order_id,)
        ).fetchone()
        if not order:
            raise HTTPException(404, "order not found")

        paid = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS t FROM store.payments "
            "WHERE order_id = %s AND status = 'captured'",
            (order_id,),
        ).fetchone()["t"]
        refunded = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS t FROM store.refunds WHERE order_id = %s",
            (order_id,),
        ).fetchone()["t"]
        if refunded + amount > paid:
            raise HTTPException(409, "refund exceeds amount paid")

        row = conn.execute(
            """INSERT INTO store.refunds
               (refund_id, idempotency_key, order_id, customer_id, amount, reason, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'processed')
               ON CONFLICT (idempotency_key) DO NOTHING
               RETURNING *""",
            (
                f"RF-{uuid.uuid4().hex[:8]}",
                idempotency_key,
                order_id,
                order["customer_id"],
                amount,
                reason,
            ),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT * FROM store.refunds WHERE idempotency_key = %s", (idempotency_key,)
            ).fetchone()
            return {**row, "created": False}
    return {**row, "created": True}


def get_ticket(ticket_id: str):
    maybe_fail("tickets")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM store.tickets WHERE ticket_id = %s", (ticket_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "ticket not found")
    return row


def update_ticket(ticket_id: str, status: str, note: str | None):
    maybe_fail("tickets")
    with get_conn() as conn:
        row = conn.execute(
            """UPDATE store.tickets
               SET status = %s,
                   notes = CASE WHEN %s::text IS NULL THEN notes
                                ELSE COALESCE(notes || E'\\n', '') || %s::text END,
                   updated_at = now()
               WHERE ticket_id = %s RETURNING *""",
            (status, note, note, ticket_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "ticket not found")
    return row


def send_email(to: str, subject: str, body: str):
    maybe_fail("email")
    with get_conn() as conn:
        return conn.execute(
            "INSERT INTO store.emails (to_email, subject, body) VALUES (%s,%s,%s) RETURNING *",
            (to, subject, body),
        ).fetchone()
