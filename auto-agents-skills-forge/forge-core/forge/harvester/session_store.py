import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTEXT_DIR = ROOT / ".context"
SESSION_PATH = CONTEXT_DIR / "last_session.json"


def _ensure_context_dir() -> None:
  CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def save_session(bundle: dict) -> None:
  _ensure_context_dir()
  SESSION_PATH.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


def load_session() -> dict:
  if not SESSION_PATH.exists():
    raise FileNotFoundError("No session bundle persisted yet.")
  return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
