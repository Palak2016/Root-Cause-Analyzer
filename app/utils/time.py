"""
Time utilities for the Root Cause Analyzer.
Provides functions for time window calculations and timestamp handling.
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, List


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    """Parse ISO format timestamp string to datetime."""
    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return to_utc(dt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse timestamp: {value}")


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO format string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def time_window(
    center: datetime,
    before: timedelta = timedelta(minutes=30),
    after: timedelta = timedelta(minutes=5),
) -> Tuple[datetime, datetime]:
    """
    Calculate a time window around a center point.

    Args:
        center: The center timestamp
        before: Duration before center
        after: Duration after center

    Returns:
        Tuple of (start, end) timestamps
    """
    return (center - before, center + after)


def bucket_timestamps(
    timestamps: List[datetime],
    bucket_size: timedelta = timedelta(seconds=30),
) -> dict:
    """
    Group timestamps into time buckets.

    Args:
        timestamps: List of timestamps to bucket
        bucket_size: Size of each bucket

    Returns:
        Dict mapping bucket key to list of indices
    """
    buckets = {}
    bucket_seconds = bucket_size.total_seconds()

    for idx, ts in enumerate(timestamps):
        bucket_key = int(ts.timestamp() // bucket_seconds)
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(idx)

    return buckets


def bucket_key_to_timestamp(bucket_key: int, bucket_size: timedelta) -> datetime:
    """Convert bucket key back to timestamp."""
    bucket_seconds = bucket_size.total_seconds()
    return datetime.fromtimestamp(bucket_key * bucket_seconds, tz=timezone.utc)


def is_within_window(
    timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    """Check if timestamp is within a time window."""
    return window_start <= timestamp <= window_end


def time_diff_seconds(start: datetime, end: datetime) -> float:
    """Calculate difference between two timestamps in seconds."""
    return (end - start).total_seconds()


def time_diff_ms(start: datetime, end: datetime) -> float:
    """Calculate difference between two timestamps in milliseconds."""
    return time_diff_seconds(start, end) * 1000


def align_to_interval(
    dt: datetime,
    interval: timedelta,
    align: str = "floor",
) -> datetime:
    """
    Align timestamp to interval boundary.

    Args:
        dt: Timestamp to align
        interval: Interval size
        align: "floor" (round down) or "ceil" (round up)

    Returns:
        Aligned timestamp
    """
    interval_seconds = interval.total_seconds()
    ts = dt.timestamp()

    if align == "floor":
        aligned_ts = (ts // interval_seconds) * interval_seconds
    else:
        aligned_ts = ((ts // interval_seconds) + 1) * interval_seconds

    return datetime.fromtimestamp(aligned_ts, tz=timezone.utc)


def sliding_windows(
    start: datetime,
    end: datetime,
    window_size: timedelta,
    step: timedelta,
) -> List[Tuple[datetime, datetime]]:
    """
    Generate sliding time windows.

    Args:
        start: Start of time range
        end: End of time range
        window_size: Size of each window
        step: Step size between windows

    Returns:
        List of (window_start, window_end) tuples
    """
    windows = []
    current = start

    while current + window_size <= end:
        windows.append((current, current + window_size))
        current += step

    return windows


def temporal_precedence_score(
    event_time: datetime,
    reference_time: datetime,
    max_lookback: timedelta = timedelta(hours=1),
) -> float:
    """
    Calculate temporal precedence score.
    Higher score means event occurred earlier (better candidate for root cause).

    Args:
        event_time: When the event occurred
        reference_time: Reference point (e.g., incident detection time)
        max_lookback: Maximum lookback window

    Returns:
        Score between 0.0 and 1.0
    """
    diff = time_diff_seconds(event_time, reference_time)

    if diff <= 0:
        # Event occurred after reference - low score
        return 0.1

    max_seconds = max_lookback.total_seconds()

    if diff > max_seconds:
        # Event too far in the past
        return 0.2

    # Linear scale: 30 minutes before = 1.0, 0 minutes = 0.5
    return 0.5 + (diff / max_seconds) * 0.5
