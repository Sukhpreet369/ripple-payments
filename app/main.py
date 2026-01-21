import os
from fastapi import FastAPI, Depends, BackgroundTasks, Header, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from .db import Base, engine, get_db, SessionLocal
from .models import Payment, PaymentStatus
from .schemas import PaymentCreate, PaymentOut
from .fx_client import FxClient
from .worker import process_payment

FX_URL = os.getenv("FX_URL", "http://localhost:8080")  # change to match Ripple FX service
FX_TIMEOUT = float(os.getenv("FX_TIMEOUT", "3.0"))
FX_RETRIES = int(os.getenv("FX_RETRIES", "3"))

fx_client = FxClient(base_url=FX_URL, timeout_seconds=FX_TIMEOUT, max_retries=FX_RETRIES)

app = FastAPI(title="Cross-Currency Payment Service", version="1.0.0")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def to_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        sender=p.sender,
        receiver=p.receiver,
        amount=Decimal(str(p.amount)),
        source_currency=p.source_currency,
        destination_currency=p.destination_currency,
        status=p.status.value,
        fx_rate=Decimal(str(p.fx_rate)) if p.fx_rate is not None else None,
        payout_amount=Decimal(str(p.payout_amount)) if p.payout_amount is not None else None,
        error_code=p.error_code,
        error_message=p.error_message,
        attempt_count=p.attempt_count,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/payments", response_model=PaymentOut, status_code=202)
def create_payment(
    payload: PaymentCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, convert_underscores=False),
):
    # Optional idempotency: if key exists, return existing record
    if idempotency_key:
        existing = db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
        if existing:
            return to_out(existing)

    if payload.source_currency == payload.destination_currency:
        # still valid in real life, but usually pointless; treat as valid with rate=1
        # (you can flip this to reject if desired)
        payment = Payment(
            idempotency_key=idempotency_key,
            sender=payload.sender,
            receiver=payload.receiver,
            amount=float(payload.amount),
            source_currency=payload.source_currency,
            destination_currency=payload.destination_currency,
            status=PaymentStatus.SUCCEEDED,
            fx_rate=1.0,
            payout_amount=float(payload.amount),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return to_out(payment)

    payment = Payment(
        idempotency_key=idempotency_key,
        sender=payload.sender,
        receiver=payload.receiver,
        amount=float(payload.amount),
        source_currency=payload.source_currency,
        destination_currency=payload.destination_currency,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # async processing so slow FX doesn't block API response
    def job(pid: str):
        job_db = SessionLocal()
        try:
            process_payment(job_db, pid, fx_client)
        finally:
            job_db.close()

    background.add_task(job, payment.id)

    return to_out(payment)


@app.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="payment not found")
    return to_out(payment)
