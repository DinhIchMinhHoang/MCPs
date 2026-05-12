import json
import subprocess
import sys
from pathlib import Path


def _cli_path() -> Path:
  return Path(sys.executable).parent / "notebooklm-mcp.EXE"


def run_notebooklm(payload: dict, command: str) -> dict:
  proc = subprocess.run(
    [str(_cli_path()), command],
    input=json.dumps(payload),
    text=True,
    capture_output=True,
    check=False
  )
  if proc.returncode != 0:
    return {"schema_version": "1.0", "error": proc.stderr.strip() or "NotebookLM CLI failed"}
  try:
    parsed = json.loads(proc.stdout)
  except json.JSONDecodeError:
    parsed = {"raw": proc.stdout.strip()}
  return {"schema_version": "1.0", "result": parsed}
