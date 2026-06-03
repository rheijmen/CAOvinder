"""Path-safety helpers for the read-only serving layer.

`cao_id` values originate from public API URLs and are used to build filesystem
paths to sidecar/SETU files. Treat them as untrusted: a value containing path
separators or a `..` sequence must never be allowed to escape the data directory.
"""

from __future__ import annotations

_UNSAFE_TOKENS = ("/", "\\", "..", "\x00")


def is_safe_cao_id(cao_id: str) -> bool:
    """Return True only for a plain filename stem (no separators, no traversal, non-empty)."""
    return bool(cao_id) and not any(token in cao_id for token in _UNSAFE_TOKENS)
