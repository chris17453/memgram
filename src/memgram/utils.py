"""Utility helpers for memgram."""

import re
import uuid
from datetime import datetime, timezone


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(value: str) -> str:
    """Normalize a name to lowercase with hyphens as separators.

    Ensures consistent matching regardless of separators or casing:
        'oxide-os', 'oxide_os', 'Oxide OS' → 'oxide-os'
    """
    # Replace underscores and whitespace with hyphens, lowercase, strip non-alnum/hyphen
    s = re.sub(r'[_\s]+', '-', value.lower().strip())
    s = re.sub(r'[^a-z0-9-]', '', s)
    # Collapse multiple hyphens and strip leading/trailing
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s
