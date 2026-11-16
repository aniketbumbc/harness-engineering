from datetime import datetime, timezone
from decimal import Decimal

from shared.settings import settings

from .models import CaseType, PolicyResult


def _d(x) -> Decimal:
    return Decimal(str(x))


def evaluate(case_type, order: dict, payments: list[dict], refunds_90d: int,
             now: datetime | None = None) -> PolicyResult:
    """Pure function: same input, same output. No network, no database."""
    now = now or datetime.now(timezone.utc)
    case_type = CaseType(case_type)
    hits: list[str] = []
    flags: list[str] = []

    def result(decision, amount="0", approval=False):
        return PolicyResult(decision=decision, allowed_amount=_d(amount),
                            requires_approval=approval, risk_flags=flags, rule_hits=hits)

    captured = sum((_d(p["amount"]) for p in payments if p["status"] == "captured"),
                   Decimal("0"))
    order_amount = _d(order["amount"])

    # 1. Not delivered, or nothing was paid: a human must look
    if not order.get("delivered_at") or captured <= 0:
        hits.append("R1_not_delivered_or_unpaid")
        return result("escalate")

    # 2. Frequent refunder: always escalate
    if refunds_90d >= 3:
        flags.append("frequent_refunder")
        hits.append("R2_three_or_more_refunds_90d")
        return result("escalate")

    # 3. Return window (a duplicate charge is a billing error, so it is exempt)
    if case_type != CaseType.duplicate_charge:
        delivered = datetime.fromisoformat(str(order["delivered_at"]))
        if (now - delivered).days > int(order["return_window_days"]):
            hits.append("R3_outside_return_window")
            return result("deny")

    # 4. Unknown claim type
    if case_type == CaseType.other:
        hits.append("R4_unknown_case_type")
        return result("escalate")

    # 5. Work out the amount
    if case_type == CaseType.duplicate_charge:
        amount = captured - order_amount
        if amount <= 0:
            hits.append("R5_no_duplicate_found")
            return result("escalate")
        hits.append("R5_duplicate_amount")
    else:
        amount = order_amount

    # 6. Approval threshold
    if amount >= settings.refund_approval_threshold:
        hits.append("R6_over_threshold_needs_approval")
        return result("refund", amount, approval=True)
    hits.append("R6_under_threshold_auto")
    return result("refund", amount)