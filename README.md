# Cross-Currency Payment Service (Reference Solution)

## What it does
- POST /payments stores a payment request and processes it asynchronously.
- Calls an FX service to fetch a conversion rate.
- Computes payout = amount * fx_rate.
- Marks payment SUCCEEDED or FAILED.
- GET /payments/{id} retrieves status, payout (if any), and error diagnostics.

## Run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Set FX_URL to match the provided Ripple FX service
export FX_URL="http://localhost:8080"
uvicorn app.main:app --reload --port 8000
