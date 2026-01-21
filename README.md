Ripple Cross-Currency Payment Service
A backend service that accepts a payment request in one currency, fetches an FX rate from an FX service, computes the payout in the destination currency, stores the result, and supports retrieving payment details later.

1. Features
POST /payments: create + store a payment and process asynchronously

GET /payments/{payment_id}: retrieve payment status, payout, and diagnostics

FX integration with timeouts, retries, backoff, and defensive response parsing

SQLite persistence (payments.db)

Optional Idempotency-Key header to prevent duplicate creates

2. Requirements
Python 3.10+ recommended

Windows (CMD)

3. Setup (Windows CMD)
3.1 Create and activate a virtual environment

python -m venv .venv
.venv\Scripts\activate

3.2 Install dependencies

pip install -r requirements.txt

4. Run Locally (Windows CMD)
4.1 Start the mock FX service (Terminal 1)

This repo includes mock_fx.py so you can test end‑to‑end without the external Ripple FX repo.

python -m uvicorn mock_fx:app --port 8080

4.2 Start the payment service (Terminal 2)

set FX_URL=http://localhost:8080
python -m uvicorn app.main:app --reload --port 8000

4.3 Verify
Health check:

curl http://localhost:8000/health

Expected:

json
{"ok": true}
Swagger UI:
http://localhost:8000/docs

5. API Usage
5.1 Create a payment
Endpoint

POST http://localhost:8000/payments

Headers

Content-Type: application/json

(Optional) Idempotency-Key: abc-123

Request body

json
{
  "sender": "alice",
  "receiver": "bob",
  "amount": "100.00",
  "source_currency": "USD",
  "destination_currency": "EUR"
}
Expected

Returns 202 Accepted

Initially may be PENDING

Later becomes SUCCEEDED or FAILED

5.2 Retrieve a payment
Endpoint

GET http://localhost:8000/payments/{payment_id}
Example (SUCCEEDED)

json
{
  "status": "SUCCEEDED",
  "fx_rate": "1.1",
  "payout_amount": "110.000000",
  "error_code": null,
  "error_message": null
}
Example (FAILED)

json
{
  "status": "FAILED",
  "fx_rate": null,
  "payout_amount": null,
  "error_code": "FX_TIMEOUT",
  "error_message": "FX request timed out after retries"
}
6. Configuration (Windows CMD)
Environment variables:

FX_URL (default: http://localhost:8080)

FX_TIMEOUT (default: 3.0)

FX_RETRIES (default: 3)

Example

set FX_URL=http://localhost:8080
set FX_TIMEOUT=8
set FX_RETRIES=4

7. FX Integration Notes
The FX client calls:

Code
GET {FX_URL}/rate?source=USD&destination=EUR
It defensively parses common formats:

json
{"rate": 1.23}
{"fx_rate": 1.23}
{"fxRate": 1.23}
"1.23"
If the real FX service differs, update app/fx_client.py (FxClient.get_rate).

8. AI Usage Note
AI assistance was used to accelerate design and implementation: API structure, input validation, resilient FX integration (timeouts/retries/backoff), defensive parsing of FX responses, and edge‑case handling while ensuring failures persist clear diagnostic information for later retrieval.
