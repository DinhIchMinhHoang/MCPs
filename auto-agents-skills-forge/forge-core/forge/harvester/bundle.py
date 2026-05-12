from datetime import datetime, timezone
from uuid import uuid4


def build_bundle() -> dict:
  return {
    "schema_version": "1.0",
    "session_id": str(uuid4()),
    "metadata": {
      "created_at": datetime.now(timezone.utc).isoformat()
    },
    "events": [],
    "narrative": "Session summary pending."
  }
