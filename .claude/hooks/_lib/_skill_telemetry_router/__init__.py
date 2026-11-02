"""Advisory-only skill discovery and model-tier planning.

No telemetry is persisted and no inference request is issued here.
"""

from __future__ import annotations

from .cheap_tier_cascade import select_cheap_tier_cascade
from .discovery_telemetry import resolve_skill_slug_from_path

__all__ = ["resolve_skill_slug_from_path", "select_cheap_tier_cascade"]
