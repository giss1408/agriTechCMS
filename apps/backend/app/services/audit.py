from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditEvent


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def record(
    db: AsyncSession,
    *,
    cooperative_id: str,
    actor_id: str | None,
    entity: str,
    entity_id: str,
    action: str,
    changes: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            cooperative_id=cooperative_id,
            actor_id=actor_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            changes={k: _plain(v) for k, v in (changes or {}).items()},
        )
    )


def diff(obj: Any, updates: dict[str, Any]) -> dict[str, Any]:
    """{"field": [old, new]} for the fields that actually change."""
    out = {}
    for key, new in updates.items():
        old = getattr(obj, key)
        if old != new:
            out[key] = [_plain(old), _plain(new)]
    return out
