import json
from pathlib import Path

from forge.approval.manifest import update_manifest, manifest_entry
from forge.opencode_mirror import sync_opencode_mirror


ROOT = Path(__file__).resolve().parents[3]
DRAFT_ROOT = ROOT / "draft"
GENERATED_ROOT = ROOT / "generated"


def _draft_meta_path(kind: str, name: str) -> Path:
  return DRAFT_ROOT / f"{kind}s" / f"{name}.json"


def _find_draft(name: str) -> Path | None:
  for kind in ("tools", "skills", "agents"):
    candidate = DRAFT_ROOT / kind / f"{name}.py"
    if candidate.exists():
      return candidate
  return None


def list_drafts() -> None:
  for kind in ("tools", "skills", "agents"):
    folder = DRAFT_ROOT / kind
    if not folder.exists():
      continue
    for item in folder.glob("*.py"):
      print(f"{kind[:-1]} {item.stem}")


def approve_artifact(kind: str, name: str, sync: bool = True) -> None:
  source = DRAFT_ROOT / f"{kind}s" / f"{name}.py"
  meta_file = _draft_meta_path(kind, name)
  if not source.exists():
    raise FileNotFoundError(f"Draft not found: {kind} {name}")
  if not meta_file.exists():
    raise FileNotFoundError(f"Draft metadata not found: {kind} {name} (run synthesis first)")
  meta = json.loads(meta_file.read_text(encoding="utf-8"))
  target_dir = GENERATED_ROOT / f"{kind}s"
  target_dir.mkdir(parents=True, exist_ok=True)
  target = target_dir / source.name
  target.write_bytes(source.read_bytes())
  entry = manifest_entry(name=name, kind=kind, path=target, summary=meta.get("summary", ""))
  update_manifest(GENERATED_ROOT / "manifest.json", entry)
  source.unlink()
  meta_file.unlink()
  if sync:
    sync_opencode_mirror()


def reject_artifact(name: str, sync: bool = True) -> None:
  draft = _find_draft(name)
  if not draft:
    raise FileNotFoundError(f"Draft not found: {name}")
  draft.unlink()
  for kind in ("tools", "skills", "agents"):
    meta = DRAFT_ROOT / kind / f"{name}.json"
    if meta.exists():
      meta.unlink()
      break
  if sync:
    sync_opencode_mirror()


def auto_promote(max_per_kind: int = 10) -> dict:
  promoted: dict[str, list[str]] = {"skill": [], "agent": []}
  skipped: dict[str, list[str]] = {"skill": [], "agent": []}
  errors: list[str] = []

  for kind in ("skill", "agent"):
    folder = DRAFT_ROOT / f"{kind}s"
    if not folder.exists():
      continue
    for item in sorted(folder.glob("*.py")):
      name = item.stem
      if len(promoted[kind]) >= max_per_kind:
        skipped[kind].append(name)
        continue
      try:
        approve_artifact(kind, name, sync=False)
        promoted[kind].append(name)
      except Exception as exc:
        errors.append(f"{kind} {name}: {exc}")
  if promoted["skill"] or promoted["agent"]:
    sync_opencode_mirror()
  return {
    "promoted": promoted,
    "skipped": skipped,
    "errors": errors
  }
