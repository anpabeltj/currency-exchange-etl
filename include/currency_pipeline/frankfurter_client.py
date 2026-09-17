"""Small client for the Frankfurter exchange rate API."""

import logging

import requests

API_URL = "https://api.frankfurter.dev/v2/rates"
REQUIRED_KEYS = ("date", "base", "quote", "rate")

logger = logging.getLogger(__name__)


def validate_rows(rows, base_currency, quote_currencies):
    """Fail loudly if the API returns something we do not expect."""
    if not isinstance(rows, list):
        raise ValueError(f"Expected a list of rates, got {type(rows).__name__}")

    allowed_quotes = set(quote_currencies)

    for index, row in enumerate(rows):
        for key in REQUIRED_KEYS:
            if key not in row:
                raise ValueError(f"Row {index} is missing key '{key}': {row}")

        if row["base"] != base_currency:
            raise ValueError(f"Row {index} has unexpected base currency: {row}")

        if row["quote"] not in allowed_quotes:
            raise ValueError(f"Row {index} has unexpected quote currency: {row}")

        if row["rate"] is None or row["rate"] <= 0:
            raise ValueError(f"Row {index} has a non positive rate: {row}")


def fetch_rates(start_date, end_date, base_currency, quote_currencies, provider, timeout=30):
    """Fetch daily rates between start_date and end_date (inclusive, ISO strings)."""
    params = {
        "from": start_date,
        "to": end_date,
        "base": base_currency,
        "quotes": ",".join(quote_currencies),
        "providers": provider,
    }

    logger.info("Requesting %s with params %s", API_URL, params)
    response = requests.get(API_URL, params=params, timeout=timeout)
    response.raise_for_status()

    rows = response.json()
    validate_rows(rows, base_currency, quote_currencies)

    logger.info("Received %s rows", len(rows))
    return rows
