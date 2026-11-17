import httpx

from shared.settings import settings

from . import ledger
from .db import get_conn
from .executor import do_refund
from .store_client import StoreClient, ToolError

BASE = settings.mock_store_url
c = StoreClient(backoff=0.2)
CASE = "CASE-X1"


def fresh():
    httpx.post(f"{BASE}/admin/reset")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO harness.cases (case_id,ticket_id,customer_id,order_id,thread_id) "
            "VALUES (%s,'T-5001','C001','O1001',%s) ON CONFLICT DO NOTHING", (CASE, CASE))
        conn.execute("DELETE FROM harness.action_ledger WHERE case_id=%s", (CASE,))


def refunds_recorded():
    return len([r for r in httpx.get(f"{BASE}/admin/refunds").json() if r["order_id"] == "O1001"])


# Scenario A: run twice
fresh()
r, skipped = do_refund(CASE, "O1001", "799", "damaged", c)
print("1. first run   skipped:", skipped, "| refund:", r["refund_id"])
r, skipped = do_refund(CASE, "O1001", "799", "damaged", c)
print("2. second run  skipped:", skipped, "| refunds recorded:", refunds_recorded())

# Scenario B: fails, then resumes
fresh()
httpx.post(f"{BASE}/admin/failures", json={"target": "refund", "mode": "error", "count": 5})
try:
    do_refund(CASE, "O1001", "799", "damaged", c)
except ToolError as e:
    print("3. failed:", e.message, "| ledger:", ledger.get(CASE, "refund")["status"])
httpx.delete(f"{BASE}/admin/failures")
r, skipped = do_refund(CASE, "O1001", "799", "damaged", c)
print("4. resumed     skipped:", skipped, "| attempts:", ledger.get(CASE, "refund")["attempts"],
      "| refunds recorded:", refunds_recorded())