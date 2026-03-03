"""Utility helpers for memgram."""

import re
import uuid
from datetime import datetime, timezone


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(value: str) -> str:
    """Normalize a name to lowercase alphanumeric only.

    Ensures consistent matching regardless of separators or casing:
        'oxide-os', 'oxide_os', 'OxideOS' → 'oxideos'
    """
    return re.sub(r'[^a-z0-9]', '', value.lower())
