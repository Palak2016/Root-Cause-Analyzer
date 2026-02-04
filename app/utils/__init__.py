"""
Utility functions for the Root Cause Analyzer.
"""

from app.utils.time import (
    utc_now,
    to_utc,
    parse_timestamp,
    format_timestamp,
    time_window,
    bucket_timestamps,
    is_within_window,
    time_diff_seconds,
    time_diff_ms,
    temporal_precedence_score,
)

from app.utils.logging import (
    setup_logging,
    get_logger,
    get_context_logger,
    set_request_id,
    get_request_id,
)

__all__ = [
    # Time utilities
    "utc_now",
    "to_utc",
    "parse_timestamp",
    "format_timestamp",
    "time_window",
    "bucket_timestamps",
    "is_within_window",
    "time_diff_seconds",
    "time_diff_ms",
    "temporal_precedence_score",
    # Logging utilities
    "setup_logging",
    "get_logger",
    "get_context_logger",
    "set_request_id",
    "get_request_id",
]
