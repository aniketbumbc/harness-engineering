import time

import httpx

from shared.settings import settings


class ToolError(Exception):
    """Structured failure. Agents and the executor read these fields, not strings."""

    def __init__(self, tool: str, message: str, status: int | None = None,
                 outcome_unknown: bool = False):
        super().__init__(f"{tool}: {message}")
        self.tool = tool
        self.message = message
        self.status = status
        self.outcome_unknown = outcome_unknown   # True = the action MAY have happened

    def to_dict(self) -> dict:
        return {"tool": self.tool, "error": self.message, "status": self.status,
                "outcome_unknown": self.outcome_unknown}


class StoreClient:
    def __init__(self, base_url: str | None = None, timeout: float = 5.0,
                 max_attempts: int = 3, backoff: float = 0.5):
        self._http = httpx.Client(base_url=base_url or settings.mock_store_url, timeout=timeout)
        self.max_attempts = max_attempts
        self.backoff = backoff

    def _call(self, tool: str, method: str, path: str, *, idempotent: bool, **kwargs):
        last: ToolError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                r = self._http.request(method, path, **kwargs)
            except httpx.ConnectError:
                last = ToolError(tool, "connection failed")          # never arrived: safe
            except httpx.TransportError as e:                        # includes timeouts
                last = ToolError(tool, f"no response ({type(e).__name__})", outcome_unknown=True)
                if not idempotent:
                    raise last                                       # unsafe to retry blindly
            else:
                if r.is_success:
                    return r.json()
                detail = r.json().get("detail", r.text) if r.content else r.text
                if r.status_code == 503:
                    last = ToolError(tool, str(detail), status=503)  # failed before acting: safe
                elif r.status_code >= 500:
                    last = ToolError(tool, str(detail), status=r.status_code, outcome_unknown=True)
                    if not idempotent:
                        raise last
                else:
                    raise ToolError(tool, str(detail), status=r.status_code)  # our fault, no retry
            if attempt < self.max_attempts:
                time.sleep(self.backoff * 2 ** (attempt - 1))
        raise last

    # ---- read tools (always idempotent) ----
    def get_ticket(self, ticket_id: str) -> dict:
        return self._call("get_ticket", "GET", f"/tickets/{ticket_id}", idempotent=True)

    def get_order(self, order_id: str) -> dict:
        return self._call("get_order", "GET", f"/orders/{order_id}", idempotent=True)

    def get_tracking(self, order_id: str) -> dict:
        return self._call("get_tracking", "GET", f"/orders/{order_id}/tracking", idempotent=True)

    def get_payments(self, order_id: str) -> dict:
        return self._call("get_payments", "GET", f"/orders/{order_id}/payments", idempotent=True)

    def get_refund_history(self, customer_id: str, days: int = 90) -> dict:
        return self._call("get_refund_history", "GET", f"/customers/{customer_id}/refunds",
                          idempotent=True, params={"days": days})

    # ---- write tools ----
    def issue_refund(self, order_id: str, amount: str, reason: str, idempotency_key: str) -> dict:
        # Idempotent BECAUSE of the key, so ambiguous failures can be retried safely.
        return self._call("issue_refund", "POST", "/refunds", idempotent=True,
                          headers={"Idempotency-Key": idempotency_key},
                          json={"order_id": order_id, "amount": amount, "reason": reason})

    def update_ticket(self, ticket_id: str, status: str, note: str | None = None) -> dict:
        # Appends a note, so a blind retry could duplicate it: not treated as idempotent.
        return self._call("update_ticket", "PATCH", f"/tickets/{ticket_id}", idempotent=False,
                          json={"status": status, "note": note})

    def send_email(self, to: str, subject: str, body: str) -> dict:
        # No idempotency key in the mock API: an ambiguous failure must NOT auto-retry.
        return self._call("send_email", "POST", "/emails", idempotent=False,
                          json={"to": to, "subject": subject, "body": body})