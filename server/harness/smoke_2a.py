import httpx

from shared.settings import settings

from .audit import log_event
from .db import get_conn
from .init_db import run as init_db
from .store_client import StoreClient, ToolError

BASE = settings.mock_store_url
c = StoreClient(backoff=0.2)


def failures(target, mode="error", count=1, delay=8):
    httpx.post(f"{BASE}/admin/failures",
               json={"target": target, "mode": mode, "count": count, "delay": delay})


# clean slate
init_db()
httpx.post(f"{BASE}/admin/reset")
with get_conn() as conn:
    conn.execute("""INSERT INTO harness.cases (case_id, ticket_id, customer_id, order_id, thread_id)
                    VALUES ('CASE-SMOKE','T-5001','C001','O1001','CASE-SMOKE')
                    ON CONFLICT DO NOTHING""")

print("1. read:", c.get_order("O1001")["item_name"])

failures("tracking", count=2)
print("2. retry then succeed:", len(c.get_tracking("O1003")["events"]), "events")

failures("tracking", count=5)
try:
    c.get_tracking("O1003")
except ToolError as e:
    print("3. gave up after retries:", e.to_dict())
httpx.delete(f"{BASE}/admin/failures")

r1 = c.issue_refund("O1001", "799", "damaged", "CASE-SMOKE:refund")
r2 = c.issue_refund("O1001", "799", "damaged", "CASE-SMOKE:refund")
print("4. refund created:", r1["created"], "| replay created:", r2["created"],
      "| same id:", r1["refund_id"] == r2["refund_id"])

failures("email", mode="timeout", count=1, delay=8)
try:
    c.send_email("riya@example.com", "Hi", "test")
except ToolError as e:
    print("5. email timeout:", e.to_dict())
httpx.delete(f"{BASE}/admin/failures")

log_event("CASE-SMOKE", "smoke", "done", {"ok": True})
with get_conn() as conn:
    n = conn.execute("SELECT count(*) AS n FROM harness.audit_events WHERE case_id='CASE-SMOKE'").fetchone()["n"]
print("6. audit rows:", n)