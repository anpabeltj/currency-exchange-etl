from datetime import date

import pytest

from currency_pipeline.date_range import resolve_date_range

RUN_DATE = date(2026, 9, 17)
HISTORY = "2020-01-01"


def test_empty_table_loads_full_history():
    result = resolve_date_range(RUN_DATE, 7, HISTORY, latest_loaded_date=None)
    assert result == ("2020-01-01", "2026-09-17")


def test_normal_run_uses_lookback():
    result = resolve_date_range(RUN_DATE, 7, HISTORY, latest_loaded_date=date(2026, 9, 16))
    assert result == ("2026-09-10", "2026-09-17")


def test_missed_runs_extend_back_to_latest_loaded_date():
    result = resolve_date_range(RUN_DATE, 7, HISTORY, latest_loaded_date=date(2026, 8, 20))
    assert result == ("2026-08-20", "2026-09-17")


def test_manual_params_win():
    result = resolve_date_range(
        RUN_DATE, 7, HISTORY,
        latest_loaded_date=date(2026, 9, 16),
        start_override="2015-01-01",
        end_override="2015-12-31",
    )
    assert result == ("2015-01-01", "2015-12-31")


def test_start_after_end_fails():
    with pytest.raises(ValueError):
        resolve_date_range(RUN_DATE, 7, HISTORY, start_override="2027-01-01")