import json
from pathlib import Path

import jsonschema


def test_rag_bundle_schema():
  schema_path = Path(__file__).resolve().parents[2] / "schemas" / "rag.bundle.schema.json"
  schema = json.loads(schema_path.read_text(encoding="utf-8"))
  payload = {
    "schema_version": "1.0",
    "session_id": "test-session",
    "events": [],
    "narrative": "Summary"
  }
  jsonschema.validate(instance=payload, schema=schema)
