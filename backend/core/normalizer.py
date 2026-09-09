"""Convert parser output into CanonicalEvent constructor data."""

from datetime import datetime, timezone
from typing import Any, Dict


class EventNormalizer:
    """Build nested canonical fields without discarding parser output."""

    def normalize(
        self,
        fields: Dict[str, Any],
        unmapped: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Return nested event data and a copied unmapped-field dictionary."""
        normalized: Dict[str, Any] = {
            "source": {},
            "destination": {},
            "network": {},
            "event": {},
            "observer": {},
        }
        remaining = dict(unmapped)

        for key, value in fields.items():
            if "." in key:
                section, field = key.split(".", 1)
                if section in normalized:
                    normalized[section][field] = value
                else:
                    remaining[key] = value
            elif key == "timestamp":
                normalized["timestamp"] = self._parse_timestamp(value)
            else:
                remaining[key] = value

        normalized.setdefault("timestamp", datetime.now(timezone.utc))
        return normalized, remaining

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        """Parse common ISO timestamps while retaining a safe UTC fallback."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            candidate = value.strip().replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                pass
        return datetime.now(timezone.utc)
