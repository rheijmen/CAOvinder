"""Path-safety helpers for the read-only serving layer.

`cao_id` values originate from public API URLs and are used to build filesystem
paths to sidecar/SETU files. Treat them as untrusted: only a plain filename stem
(starting with an alphanumeric, containing only alphanumerics, '.', '-', '_') is
allowed, which rules out path separators, `..` traversal, NUL bytes, leading dots
and whitespace-only values.
"""

from __future__ import annotations

import re

_SAFE_CAO_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def is_safe_cao_id(cao_id: str) -> bool:
    """Return True only for a plain filename stem (see module docstring)."""
    return bool(_SAFE_CAO_ID.fullmatch(cao_id))
