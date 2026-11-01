"""Actions.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
from .actions_core import _ACTIONS as _CORE_ACTIONS
from .actions_extended import _ACTIONS as _EXTENDED_ACTIONS

__all__ = ('_KNOWN_ACTIONS', 'EVENT_SCHEMA_V2')

_KNOWN_ACTIONS = _CORE_ACTIONS | _EXTENDED_ACTIONS


# Event schema version marker — bump only on breaking change
EVENT_SCHEMA_V2 = "v2"
