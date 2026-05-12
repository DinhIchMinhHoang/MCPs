import json
import re
from pathlib import Path

from forge.synthesizer.dedup import ArtifactInfo, find_similar
from forge.approval.manifest import load_manifest


DRAFT_ROOT = Path(__file__).resolve().parents[3] / "draft"
GENERATED_ROOT = Path(__file__).resolve().parents[3] / "generated"


def _draft_path(kind: str, name: str) -> Path:
  return DRAFT_ROOT / f"{kind}s" / f"{name}.py"


def _draft_meta_path(kind: str, name: str) -> Path:
  return DRAFT_ROOT / f"{kind}s" / f"{name}.json"


def _summary_from_payload(payload: dict) -> str:
  return payload.get("summary", "Generated artifact proposal.")  # kept for compatibility


def _materialize(kind: str, name: str, body: str, summary: str) -> Path:
  path = _draft_path(kind, name)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(body, encoding="utf-8")
  meta = {
    "name": name,
    "kind": kind,
    "summary": summary
  }
  _draft_meta_path(kind, name).write_text(json.dumps(meta), encoding="utf-8")
  return path


def _merge_standout(existing: ArtifactInfo, proposal: dict, proposal_summary: str) -> tuple[str, str]:
  merged_summary = f"Merged {existing.name} with {proposal_summary}"
  body = (
    f'"""Merged standout artifact based on {existing.name}."""\n\n'
    f"SUMMARY = {json.dumps(merged_summary)}\n"
  )
  return body, merged_summary


def _parse_proposals(text: str) -> list[dict]:
  parsed = None
  if text.strip().startswith("{"):
    try:
      parsed = json.loads(text)
    except json.JSONDecodeError:
      pass

  if parsed and isinstance(parsed, dict) and "answer" in parsed:
    text = parsed["answer"]

  pattern = re.compile(r"^(TOOL|SKILL|AGENT)\s*\|\s*([^\|]+?)\s*\|\s*(.+)$", re.IGNORECASE)
  proposals: list[dict] = []
  for raw_line in text.splitlines():
    line = raw_line.strip().replace("**", "").replace("*", "")
    if not line:
      continue
    m = pattern.match(line)
    if not m:
      continue
    kind = m.group(1).strip().lower()
    name = m.group(2).strip()
    summary = m.group(3).strip()
    if not name or kind not in {"tool", "skill", "agent"}:
      continue
    proposals.append({"type": kind, "name": name, "summary": summary})
  return proposals


def generate_drafts(rag_output: dict) -> dict:
  text = rag_output.get("result", {}).get("text", "")
  proposals = _parse_proposals(text)
  if not proposals:
    return {"schema_version": "1.0", "status": "no_proposals", "drafts_written": 0}

  manifest = load_manifest(GENERATED_ROOT / "manifest.json")
  existing_items = [
    ArtifactInfo(
      name=item["name"],
      kind=item["type"],
      summary=item.get("summary", ""),
      path=item["path"]
    )
    for item in manifest.get("artifacts", [])
  ]

  seen: list[ArtifactInfo] = []
  written = 0
  for proposal in proposals:
    kind = proposal.get("type")
    name = proposal.get("name")
    if kind not in {"tool", "skill", "agent"} or not name:
      continue
    summary = _summary_from_payload(proposal)
    target = ArtifactInfo(name=name, kind=kind, summary=summary, path="")
    candidates = [item for item in existing_items if item.kind == kind]
    match, score = find_similar(target, candidates + seen)
    if match and score > 0.80:
      body, summary = _merge_standout(match, proposal, summary)
    else:
      body = (
        f'"""Generated {kind}."""\n\n'
        f"SUMMARY = {json.dumps(summary)}\n"
      )
    _materialize(kind, name, body, summary)
    seen.append(target)
    written += 1
  return {"schema_version": "1.0", "status": "drafts_generated", "drafts_written": written}
