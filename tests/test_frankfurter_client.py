import pytest

from currency_pipeline.frankfurter_client import validate_rows

QUOTES = ["IDR", "MYR", "SGD"]


def make_row(quote="IDR", rate=16500.25, base="USD"):
    return {"date": "2026-09-15", "base": base, "quote": quote, "rate": rate}


def test_valid_rows_pass():
    rows = [make_row("IDR"), make_row("MYR", 4.21), make_row("SGD", 1.29)]
    validate_rows(rows, "USD", QUOTES)


def test_empty_list_is_allowed():
    validate_rows([], "USD", QUOTES)


def test_missing_key_fails():
    row = make_row()
    del row["rate"]
    with pytest.raises(ValueError, match="missing key"):
        validate_rows([row], "USD", QUOTES)


def test_unexpected_quote_fails():
    with pytest.raises(ValueError, match="unexpected quote"):
        validate_rows([make_row("JPY")], "USD", QUOTES)


def test_unexpected_base_fails():
    with pytest.raises(ValueError, match="unexpected base"):
        validate_rows([make_row(base="EUR")], "USD", QUOTES)


def test_non_positive_rate_fails():
    with pytest.raises(ValueError, match="non positive"):
        validate_rows([make_row(rate=0)], "USD", QUOTES)


def test_response_must_be_list():
    with pytest.raises(ValueError, match="Expected a list"):
        validate_rows({"message": "error"}, "USD", QUOTES)
