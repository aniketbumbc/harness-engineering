from fastapi import APIRouter, Header

from .functions import (
    check_health,
    clear_failures,
    create_refund,
    customer_refunds,
    get_failures,
    get_order,
    get_payments,
    get_ticket,
    get_tracking,
    list_emails,
    list_refunds,
    reset_store,
    send_email,
    set_failure,
    update_ticket,
)
from .models import EmailIn, FailureIn, RefundIn, TicketPatch

router = APIRouter()


@router.post("/admin/failures")
def set_failure_endpoint(body: FailureIn):
    return set_failure(body.target, body.mode, body.count, body.delay)


@router.get("/admin/failures")
def get_failures_endpoint():
    return get_failures()


@router.delete("/admin/failures")
def clear_failures_endpoint():
    return clear_failures()


@router.post("/admin/reset")
def reset_endpoint():
    return reset_store()


@router.get("/admin/refunds")
def all_refunds():
    return list_refunds()


@router.get("/admin/emails")
def all_emails():
    return list_emails()


@router.get("/health")
def health():
    return check_health()


@router.get("/orders/{order_id}")
def get_order_endpoint(order_id: str):
    return get_order(order_id)


@router.get("/orders/{order_id}/tracking")
def get_tracking_endpoint(order_id: str):
    return get_tracking(order_id)


@router.get("/orders/{order_id}/payments")
def get_payments_endpoint(order_id: str):
    return get_payments(order_id)


@router.get("/customers/{customer_id}/refunds")
def customer_refunds_endpoint(customer_id: str, days: int = 90):
    return customer_refunds(customer_id, days)


@router.post("/refunds")
def create_refund_endpoint(body: RefundIn, idempotency_key: str = Header(..., alias="Idempotency-Key")):
    return create_refund(body.order_id, body.amount, body.reason, idempotency_key)


@router.get("/tickets/{ticket_id}")
def get_ticket_endpoint(ticket_id: str):
    return get_ticket(ticket_id)


@router.patch("/tickets/{ticket_id}")
def update_ticket_endpoint(ticket_id: str, body: TicketPatch):
    return update_ticket(ticket_id, body.status, body.note)


@router.post("/emails")
def send_email_endpoint(body: EmailIn):
    return send_email(body.to, body.subject, body.body)
