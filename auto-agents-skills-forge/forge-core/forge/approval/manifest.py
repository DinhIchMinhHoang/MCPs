import json
from datetime import datetime, timezone
from pathlib import Path
from hashlib import sha256


def load_manifest(path: Path) -> dict:
  if not path.exists():
    return {
      "schema_version": "1.0",
      "generated_at": datetime.now(timezone.utc).isoformat(),
      "artifacts": []
    }
  return json.loads(path.read_text(encoding="utf-8"))


def _hash_file(path: Path) -> str:
  return sha256(path.read_bytes()).hexdigest()


def update_manifest(path: Path, entry: dict) -> None:
  manifest = load_manifest(path)
  manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
  artifacts = [a for a in manifest.get("artifacts", []) if a.get("name") != entry["name"]]
  artifacts.append(entry)
  manifest["artifacts"] = artifacts
  path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def manifest_entry(name: str, kind: str, path: Path, summary: str) -> dict:
  return {
    "name": name,
    "type": kind,
    "version": "0.1.0",
    "hash": _hash_file(path),
    "path": str(path).replace("\\", "/"),
    "summary": summary,
    "dependencies": []
  }
