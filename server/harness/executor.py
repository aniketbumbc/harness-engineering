from . import ledger
from .audit import log_event
from .store_client import StoreClient, ToolError


def _step(case_id: str, action: str, request: dict, fn):
    """Run one side effect through the ledger. Returns (response, skipped)."""
    row = ledger.begin(case_id, action, request)
    if row is None:                                   # already 'done': never repeat it
        log_event(case_id, "executor", f"{action}_skipped", {"reason": "already done"})
        return ledger.get(case_id, action)["response"], True
    try:
        response = fn(row["idempotency_key"])
    except ToolError as e:
        ledger.mark_failed(case_id, action, str(e))
        log_event(case_id, "executor", f"{action}_failed", e.to_dict())
        raise
    ledger.mark_done(case_id, action, response)
    log_event(case_id, "executor", f"{action}_done", {"attempts": row["attempts"]})
    return response, False


def do_refund(case_id: str, order_id: str, amount, reason: str, client: StoreClient):
    request = {"order_id": order_id, "amount": str(amount), "reason": reason}
    return _step(case_id, "refund", request,
                 lambda key: client.issue_refund(order_id, str(amount), reason, key))