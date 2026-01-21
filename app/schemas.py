from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, field_validator
import re
from typing import Optional


CURRENCY_RE = re.compile(r"^[A-Z]{3,8}$")  # allow ISO4217 + some crypto-like codes


class PaymentCreate(BaseModel):
    sender: str = Field(min_length=1, max_length=128)
    receiver: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=Decimal("0"))
    source_currency: str = Field(min_length=3, max_length=8)
    destination_currency: str = Field(min_length=3, max_length=8)

    @field_validator("source_currency", "destination_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if not CURRENCY_RE.match(v):
            raise ValueError("currency must be uppercase letters (3-8 chars), e.g., USD, EUR, XRP")
        return v

    @field_validator("sender", "receiver")
    @classmethod
    def strip_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class PaymentOut(BaseModel):
    id: str
    sender: str
    receiver: str
    amount: Decimal
    source_currency: str
    destination_currency: str
    status: str

    fx_rate: Optional[Decimal] = None
    payout_amount: Optional[Decimal] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None

    attempt_count: int
    created_at: str
    updated_at: str


def quantize_money(x: Decimal, places: int = 6) -> Decimal:
    # Use 6 decimals to be safe across fiat/crypto; adjust if you know currency-specific decimals.
    q = Decimal("1." + "0" * places)
    return x.quantize(q, rounding=ROUND_HALF_UP)
