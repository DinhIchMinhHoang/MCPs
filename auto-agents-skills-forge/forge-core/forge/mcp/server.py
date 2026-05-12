import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from forge.harvester.redact import redact_bundle
from forge.harvester.session_store import load_session, save_session
from forge.synthesizer.generator import generate_drafts
from forge.synthesizer.notebook_manager import get_manager
from forge.loader import list_generated, describe_generated, invoke_generated
from forge.opencode_mirror import sync_opencode_mirror
from forge.approval.promote import auto_promote


GENERATED_ROOT = Path(__file__).resolve().parents[3] / "generated"
MANIFEST_PATH = GENERATED_ROOT / "manifest.json"


mcp = FastMCP("forge")




@mcp.tool()
def ingest_session(bundle: dict) -> dict:
  if bundle.get("schema_version") != "1.0":
    return {"schema_version": "1.0", "error": "Invalid schema_version"}
  redacted = redact_bundle(bundle)
  save_session(redacted)
  get_manager().ingest_to_notebook(redacted)
  return {"schema_version": "1.0", "status": "ok"}


@mcp.tool()
def query_rag_tool(prompt: str | None = None) -> dict:
  prompt_text = prompt or (
    "Based on this session, propose new tools, skills, and agents. "
    "Always include a Plan agent named Plan_Agent and propose subagents + skills to execute the plan. "
    "Format each line as: TOOL|<name>|<summary>, SKILL|<name>|<summary>, AGENT|<name>|<summary>."
  )
  return get_manager().query_notebook(prompt_text)


@mcp.tool()
def trigger_synthesis() -> dict:
  rag_output = query_rag_tool()
  drafts = generate_drafts(rag_output)
  promotion = auto_promote()
  return {
    "schema_version": "1.0",
    "status": drafts.get("status"),
    "drafts_written": drafts.get("drafts_written", 0),
    "auto_promoted": promotion
  }


@mcp.tool()
def list_generated() -> dict:
  results = list_generated(MANIFEST_PATH)
  return {
    "schema_version": "1.0",
    "count": len(results),
    "artifacts": results
  }


@mcp.tool()
def describe_generated(kind: str, name: str) -> dict:
  if kind not in {"tool", "skill", "agent"}:
    return {"schema_version": "1.0", "error": f"invalid kind: {kind}"}
  result = describe_generated(MANIFEST_PATH, kind, name)
  result["schema_version"] = "1.0"
  return result


@mcp.tool()
def invoke_generated(kind: str, name: str, payload: dict | None = None) -> dict:
  if kind != "tool":
    return {
      "schema_version": "1.0",
      "error": f"{kind} is describe-only. Use describe_generated to read prompt text.",
      "kind": kind,
      "name": name
    }
  result = invoke_generated(MANIFEST_PATH, kind, name, payload or {})
  result["schema_version"] = "1.0"
  return result


@mcp.tool()
def sync_opencode() -> dict:
  result = sync_opencode_mirror()
  result["schema_version"] = "1.0"
  return result


@mcp.tool()
def list_categories() -> dict:
  from forge.opencode_mirror import list_categories
  result = list_categories()
  result["schema_version"] = "1.0"
  return result


if __name__ == "__main__":
  mcp.run()
