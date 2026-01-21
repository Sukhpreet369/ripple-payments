from decimal import Decimal
from sqlalchemy.orm import Session

from .fx_client import FxClient, FxError
from .models import Payment, PaymentStatus
from .schemas import quantize_money


def process_payment(db: Session, payment_id: str, fx: FxClient) -> None:
    payment = db.get(Payment, payment_id)
    if not payment:
        return

    # idempotent processing
    if payment.status != PaymentStatus.PENDING:
        return

    payment.attempt_count += 1

    try:
        rate = fx.get_rate(payment.source_currency, payment.destination_currency)

        amount = Decimal(str(payment.amount))
        payout = amount * rate

        payment.fx_rate = float(rate)
        payment.payout_amount = float(quantize_money(payout, places=6))
        payment.status = PaymentStatus.SUCCEEDED
        payment.error_code = None
        payment.error_message = None

    except FxError as e:
        payment.status = PaymentStatus.FAILED
        payment.error_code = e.code
        payment.error_message = e.message

    except Exception as e:
        payment.status = PaymentStatus.FAILED
        payment.error_code = "UNKNOWN_ERROR"
        payment.error_message = str(e)

    db.add(payment)
    db.commit()
