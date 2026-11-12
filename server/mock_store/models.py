from decimal import Decimal

from pydantic import BaseModel, Field


class FailureIn(BaseModel):
    target: str
    mode: str = "error"  # "error" or "timeout"
    count: int = 1  # how many upcoming calls fail
    delay: int = 15  # seconds to hang for "timeout"


class RefundIn(BaseModel):
    order_id: str
    amount: Decimal = Field(gt=0)
    reason: str


class TicketPatch(BaseModel):
    status: str
    note: str | None = None


class EmailIn(BaseModel):
    to: str
    subject: str
    body: str
