import random
import time
from decimal import Decimal
from typing import Any, Optional

import httpx


class FxError(Exception):
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _parse_rate(data: Any) -> Decimal:
    """
    Defensive parsing:
    Accepts:
      - {"rate": 1.23}
      - {"fx_rate": 1.23}
      - {"fxRate": 1.23}
      - {"result": {"rate": 1.23}}
      - 1.23
      - "1.23"
    """
    if data is None:
        raise FxError("FX_INVALID_RESPONSE", "FX response is null")

    if isinstance(data, (int, float, str)):
        try:
            r = Decimal(str(data))
            if r <= 0:
                raise FxError("FX_INVALID_RESPONSE", f"FX rate must be > 0, got {r}")
            return r
        except Exception:
            raise FxError("FX_INVALID_RESPONSE", f"FX rate is not numeric: {data}")

    if isinstance(data, dict):
        candidates = [
            data.get("rate"),
            data.get("fx_rate"),
            data.get("fxRate"),
        ]
        # nested common patterns
        if "result" in data and isinstance(data["result"], dict):
            candidates.append(data["result"].get("rate"))
            candidates.append(data["result"].get("fx_rate"))
            candidates.append(data["result"].get("fxRate"))

        for c in candidates:
            if c is None:
                continue
            try:
                r = Decimal(str(c))
                if r <= 0:
                    continue
                return r
            except Exception:
                continue

        raise FxError("FX_INVALID_RESPONSE", f"Could not find a numeric 'rate' in FX response: {data}")

    raise FxError("FX_INVALID_RESPONSE", f"Unrecognized FX response type: {type(data)}")


class FxClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 3.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=timeout_seconds)
        self.max_retries = max_retries

    def get_rate(self, source: str, dest: str) -> Decimal:
        """
        Generic FX call. Configure FX_URL to match Ripple's provided service.
        Default expects something like:
          GET {FX_URL}/rate?source=USD&destination=EUR
        If your service differs, adjust the request path/params only.
        """
        url = f"{self.base_url}/rate"
        params = {"source": source, "destination": dest}

        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, params=params)
                if resp.status_code >= 500:
                    raise FxError("FX_UPSTREAM_ERROR", f"FX service 5xx: {resp.status_code}", {"body": resp.text})
                if resp.status_code >= 400:
                    raise FxError("FX_BAD_REQUEST", f"FX service 4xx: {resp.status_code}", {"body": resp.text})

                # try JSON first; if not JSON, fallback to text
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text.strip()

                return _parse_rate(data)

            except httpx.TimeoutException as e:
                last_exc = e
                # exponential backoff + jitter
                sleep_s = (2 ** (attempt - 1)) * 0.2 + random.uniform(0, 0.1)
                time.sleep(sleep_s)

            except FxError as e:
                # retry on upstream/transient issues, fail fast on invalid response
                if e.code in {"FX_UPSTREAM_ERROR"} and attempt < self.max_retries:
                    sleep_s = (2 ** (attempt - 1)) * 0.2 + random.uniform(0, 0.1)
                    time.sleep(sleep_s)
                    last_exc = e
                    continue
                raise

            except Exception as e:
                last_exc = e
                if attempt < self.max_retries:
                    sleep_s = (2 ** (attempt - 1)) * 0.2 + random.uniform(0, 0.1)
                    time.sleep(sleep_s)
                    continue
                break

        raise FxError("FX_TIMEOUT", "FX request timed out after retries", {"cause": str(last_exc)})
