import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from forge.harvester.redact import redact_bundle
from forge.harvester.session_store import load_session, save_session
from forge.synthesizer.generator import generate_drafts
from forge.synthesizer.notebook_manager import get_manager


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
    "Format each line as: TOOL|<name>|<summary>, SKILL|<name>|<summary>, AGENT|<name>|<summary>."
  )
  return get_manager().query_notebook(prompt_text)


@mcp.tool()
def trigger_synthesis() -> dict:
  rag_output = query_rag_tool()
  return generate_drafts(rag_output)


if __name__ == "__main__":
  mcp.run()
