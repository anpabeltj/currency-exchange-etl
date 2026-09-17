"""Decide which dates each pipeline run should fetch."""

from datetime import date, timedelta


def resolve_date_range(
    end_date,
    lookback_days,
    history_start_date,
    latest_loaded_date=None,
    start_override=None,
    end_override=None,
):
    """
    Return (start, end) as ISO strings.

    1. Manual start or end params always win.
    2. Empty raw table: load the full history from history_start_date.
    3. Otherwise use the lookback window. If the pipeline missed more days
       than the window covers, start from the latest loaded date instead
       so no gap is left behind.
    """
    if end_override:
        end_date = date.fromisoformat(end_override)

    if start_override:
        start_date = date.fromisoformat(start_override)
    elif latest_loaded_date is None:
        start_date = date.fromisoformat(history_start_date)
    else:
        lookback_start = end_date - timedelta(days=lookback_days)
        start_date = min(lookback_start, latest_loaded_date)

    if start_date > end_date:
        raise ValueError(f"start_date {start_date} is after end_date {end_date}")

    return start_date.isoformat(), end_date.isoformat()