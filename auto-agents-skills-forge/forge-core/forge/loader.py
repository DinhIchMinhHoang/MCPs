import json
import importlib.util
from pathlib import Path


def _resolve_path(manifest_path: Path, entry_path: str) -> Path:
  path = Path(entry_path)
  if path.is_absolute():
    return path
  return (manifest_path.parent / path).resolve()


def load_artifact_modules(manifest_path: Path) -> list[dict]:
  if not manifest_path.exists():
    return []
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  results: list[dict] = []
  for entry in manifest.get("artifacts", []):
    name = entry.get("name", "")
    kind = entry.get("type", "artifact")
    raw_path = entry.get("path", "")
    if not raw_path:
      results.append({"name": name, "type": kind, "status": "missing", "path": ""})
      continue
    artifact_path = _resolve_path(manifest_path, raw_path)
    if not artifact_path.exists():
      results.append({"name": name, "type": kind, "status": "missing", "path": str(artifact_path)})
      continue
    module_name = f"forge.generated.{kind}.{name}"
    spec = importlib.util.spec_from_file_location(module_name, artifact_path)
    if not spec or not spec.loader:
      results.append({"name": name, "type": kind, "status": "failed", "reason": "spec_not_found"})
      continue
    module = importlib.util.module_from_spec(spec)
    try:
      spec.loader.exec_module(module)
    except Exception as exc:
      results.append({"name": name, "type": kind, "status": "failed", "reason": str(exc)})
      continue
    results.append({"name": name, "type": kind, "status": "loaded", "module": module, "path": str(artifact_path)})
  return results


def extract_prompt(module: object, kind: str) -> str | None:
  for attr in ("SYSTEM_PROMPT", "INSTRUCTION", "PROMPT"):
    if hasattr(module, attr):
      return str(getattr(module, attr))
  if kind in ("skill", "agent") and hasattr(module, "SUMMARY"):
    return str(getattr(module, "SUMMARY"))
  return None


def list_generated(manifest_path: Path) -> list[dict]:
  results = load_artifact_modules(manifest_path)
  return [
    {k: v for k, v in r.items() if k != "module"}
    for r in results
  ]


def describe_generated(manifest_path: Path, kind: str, name: str) -> dict:
  results = load_artifact_modules(manifest_path)
  for r in results:
    if r.get("name") == name and r.get("type") == kind:
      module = r.get("module")
      if module is None:
        return r
      prompt = extract_prompt(module, kind)
      summary = getattr(module, "SUMMARY", None)
      return {
        "name": name,
        "type": kind,
        "status": r.get("status"),
        "summary": str(summary) if summary else None,
        "prompt": prompt,
        "path": r.get("path")
      }
  return {"name": name, "type": kind, "status": "not_found"}


def invoke_generated(manifest_path: Path, kind: str, name: str, payload: dict) -> dict:
  if kind != "tool":
    return {
      "error": f"{kind} is describe-only. Use describe_generated() to read prompt text.",
      "kind": kind,
      "name": name
    }
  results = load_artifact_modules(manifest_path)
  for r in results:
    if r.get("name") == name and r.get("type") == kind:
      module = r.get("module")
      if module is None:
        return {"error": f"module not loaded", "status": r.get("status")}
      if not hasattr(module, "run"):
        return {"error": "artifact has no run() function", "name": name}
      try:
        return {"result": module.run(payload), "name": name}
      except Exception as exc:
        return {"error": str(exc), "name": name}
  return {"error": f"artifact not found: {kind} {name}", "status": "not_found"}


def load_generated(manifest_path: Path) -> list[dict]:
  return load_artifact_modules(manifest_path)
