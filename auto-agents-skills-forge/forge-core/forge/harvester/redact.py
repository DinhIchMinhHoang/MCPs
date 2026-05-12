import os
import re

from forge.policies.redaction_rules import RULES


def _redact_text(text: str) -> str:
  redacted = text
  for pattern, replacement in RULES:
    redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
  root_path = os.getcwd()
  if root_path:
    redacted = redacted.replace(root_path, "<REDACTED_PATH>")
  return redacted


def redact_bundle(bundle: dict) -> dict:
  redacted = dict(bundle)
  redacted["narrative"] = _redact_text(str(bundle.get("narrative", "")))
  events = bundle.get("events", [])
  clean_events = []
  for event in events:
    clean_event = {}
    for key, value in event.items():
      if isinstance(value, str):
        clean_event[key] = _redact_text(value)
      else:
        clean_event[key] = value
    clean_events.append(clean_event)
  redacted["events"] = clean_events
  return redacted
