import operator
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    damaged_item = "damaged_item"
    not_delivered = "not_delivered"
    duplicate_charge = "duplicate_charge"
    other = "other"


class Triage(BaseModel):
    case_type: CaseType
    order_id: str | None = None
    claim_summary: str


class Evidence(BaseModel):
    order: dict
    payments: list[dict]
    tracking: list[dict]
    refunds_90d: int
    summary: str                      # the Investigator's written findings


class PolicyResult(BaseModel):
    decision: Literal["refund", "deny", "escalate"]
    allowed_amount: Decimal = Decimal("0")
    requires_approval: bool = False
    risk_flags: list[str] = Field(default_factory=list)
    rule_hits: list[str] = Field(default_factory=list)   # which rules fired, for audit


class Proposal(BaseModel):
    action: Literal["refund", "deny", "escalate"]
    amount: Decimal = Decimal("0")
    reason: str
    customer_message: str


class Approval(BaseModel):
    required: bool
    status: Literal["not_required", "pending", "approved", "rejected", "modified"]
    decided_by: str | None = None
    final_amount: Decimal | None = None
    comment: str | None = None


class Execution(BaseModel):
    refund_done: bool = False
    refund_id: str | None = None
    ticket_done: bool = False
    email_done: bool = False


class CaseState(TypedDict, total=False):
    # identity
    case_id: str
    ticket_id: str
    customer_id: str
    order_id: str
    complaint: str
    # results of each stage (stored as dicts)
    memory: list[str]
    triage: dict
    evidence: dict
    policy: dict
    proposal: dict
    approval: dict
    execution: dict
    # the reducer: nodes return {"audit": [event]} and LangGraph APPENDS
    audit: Annotated[list[dict], operator.add]