import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from forge.harvester.session_store import save_session

ROOT = Path(__file__).resolve().parents[3]
CONTEXT_DIR = ROOT / ".context"
NOTEBOOK_ID_PATH = CONTEXT_DIR / "notebook_id.txt"


def _ensure_context_dir() -> None:
  CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def _cli_path() -> Path:
  return Path(sys.executable).parent / "notebooklm-mcp.EXE"


def _parse_json_from_text(text: str) -> Any | None:
  text = text.strip()
  if not text:
    return None
  try:
    return json.loads(text)
  except json.JSONDecodeError:
    pass
  start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
  if start == -1:
    return None
  for end in range(len(text), start, -1):
    if text[end - 1] in ("}", "]"):
      snippet = text[start:end]
      try:
        return json.loads(snippet)
      except json.JSONDecodeError:
        continue
  return None


def _extract_text(result: Any) -> str:
  if isinstance(result, str):
    return result
  if isinstance(result, dict):
    content = result.get("content")
    if isinstance(content, list):
      texts: list[str] = []
      for item in content:
        if not isinstance(item, dict):
          continue
        if item.get("type") == "text":
          texts.append(item.get("text", ""))
      return "\n".join([t for t in texts if t])
    if "text" in result and isinstance(result["text"], str):
      return result["text"]
  return ""


def _extract_json(result: Any) -> Any | None:
  if isinstance(result, dict):
    if "status" in result:
      return result
    content = result.get("content")
    if isinstance(content, list):
      for item in content:
        if not isinstance(item, dict):
          continue
        if item.get("type") == "json":
          if "json" in item:
            return item["json"]
          if "data" in item:
            return item["data"]
        if item.get("type") == "text":
          parsed = _parse_json_from_text(item.get("text", ""))
          if parsed is not None:
            return parsed
  if isinstance(result, str):
    return _parse_json_from_text(result)
  return None


class NotebookManager:
  def __init__(self, title: str = "Forge Sessions") -> None:
    self._title = title
    self._proc: subprocess.Popen[str] | None = None
    self._lock = threading.Lock()
    self._next_id = 1
    self._debug = os.environ.get("FORGE_NB_DEBUG", "").lower() in {"1", "true", "yes"}
    self._notebook_id = self._load_notebook_id()
    if not self._notebook_id:
      self._notebook_id = self._find_or_create_notebook()

  def _load_notebook_id(self) -> str | None:
    if NOTEBOOK_ID_PATH.exists():
      return NOTEBOOK_ID_PATH.read_text(encoding="utf-8").strip() or None
    return None

  def _save_notebook_id(self, notebook_id: str) -> None:
    _ensure_context_dir()
    NOTEBOOK_ID_PATH.write_text(notebook_id, encoding="utf-8")

  def _start_proc(self) -> None:
    if self._proc and self._proc.poll() is None:
      return
    self._proc = subprocess.Popen(
      [str(_cli_path())],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      bufsize=1
    )
    self._initialize_mcp()

  def _initialize_mcp(self) -> None:
    request_id = self._next_id
    self._next_id += 1
    init_payload = {
      "jsonrpc": "2.0",
      "id": request_id,
      "method": "initialize",
      "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "forge", "version": "0.1.0"}
      }
    }
    self._write_message(init_payload)
    self._read_response(request_id)
    self._write_message({"jsonrpc": "2.0", "method": "notifications/initialized"})

  def _write_message(self, payload: dict) -> None:
    if not self._proc or not self._proc.stdin:
      raise RuntimeError("notebooklm-mcp process not started")
    if self._debug:
      print(f"[forge-nb] -> {payload}", file=sys.stderr)
    self._proc.stdin.write(json.dumps(payload) + "\n")
    self._proc.stdin.flush()

  def _read_response(self, request_id: int, timeout: float = 120.0) -> dict:
    if not self._proc or not self._proc.stdout:
      raise RuntimeError("notebooklm-mcp process not started")
    deadline = time.time() + timeout
    while time.time() < deadline:
      line = self._proc.stdout.readline()
      if not line:
        if self._proc.poll() is not None:
          raise RuntimeError("notebooklm-mcp process exited")
        continue
      line = line.strip()
      if not line:
        continue
      try:
        msg = json.loads(line)
      except json.JSONDecodeError:
        if self._debug:
          print(f"[forge-nb] ! non-json line: {line}", file=sys.stderr)
        continue
      if self._debug:
        print(f"[forge-nb] <- {msg}", file=sys.stderr)
      if msg.get("id") == request_id:
        if "error" in msg:
          return {"schema_version": "1.0", "error": msg["error"]}
        return {"schema_version": "1.0", "result": msg.get("result")}
    raise TimeoutError("Timeout waiting for notebooklm-mcp response")

  def _tool_call(self, name: str, arguments: dict) -> dict:
    with self._lock:
      self._start_proc()
      request_id = self._next_id
      self._next_id += 1
      payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
          "name": name,
          "arguments": arguments
        }
      }
      self._write_message(payload)
      return self._read_response(request_id)

  def _find_notebook_id(self, data: Any) -> str | None:
    if isinstance(data, dict):
      if "notebook_id" in data and isinstance(data["notebook_id"], str):
        return data["notebook_id"]
      if "notebook" in data and isinstance(data["notebook"], dict):
        notebook = data["notebook"]
        for key in ("id", "uuid", "notebook_id"):
          if key in notebook and isinstance(notebook[key], str):
            return notebook[key]
      for key in ("notebooks", "items", "data"):
        if key in data:
          return self._find_notebook_id(data[key])
    if isinstance(data, list):
      for item in data:
        if not isinstance(item, dict):
          continue
        title = item.get("title") or item.get("name")
        if title == self._title:
          return item.get("id") or item.get("uuid") or item.get("notebook_id")
    return None

  def _find_or_create_notebook(self) -> str:
    list_result = self._tool_call("notebook_list", {})
    data = _extract_json(list_result.get("result")) or list_result.get("result")
    if isinstance(data, dict) and "notebooks" in data:
      notebook_id = self._find_notebook_id(data["notebooks"])
    else:
      notebook_id = self._find_notebook_id(data)
    if notebook_id:
      self._save_notebook_id(notebook_id)
      return notebook_id

    create_result = self._tool_call("notebook_create", {"title": self._title})
    data = _extract_json(create_result.get("result")) or create_result.get("result")
    notebook_id = self._find_notebook_id(data)
    if notebook_id:
      self._save_notebook_id(notebook_id)
      return notebook_id

    list_result = self._tool_call("notebook_list", {})
    data = _extract_json(list_result.get("result")) or list_result.get("result")
    if isinstance(data, dict) and "notebooks" in data:
      notebook_id = self._find_notebook_id(data["notebooks"])
    else:
      notebook_id = self._find_notebook_id(data)
    if not notebook_id:
      raise RuntimeError("Unable to resolve NotebookLM notebook id")
    self._save_notebook_id(notebook_id)
    return notebook_id

  def _bundle_to_markdown(self, bundle: dict) -> str:
    lines = [
      f"<!-- session: {bundle.get('session_id', '')} -->",
      "## Summary",
      bundle.get("narrative", ""),
      "",
      "## Events",
      "| Step | Action | Outcome |",
      "|------|--------|---------|"
    ]
    for event in bundle.get("events", []):
      step = str(event.get("step", ""))
      action = str(event.get("action", ""))
      outcome = str(event.get("outcome", ""))
      lines.append(f"| {step} | {action} | {outcome} |")
    return "\n".join(lines)

  def ingest_to_notebook(self, bundle: dict) -> dict:
    content = self._bundle_to_markdown(bundle)
    title = f"Session {bundle.get('session_id', 'unknown')}"
    payload = {
      "notebook_id": self._notebook_id,
      "source_type": "text",
      "text": content,
      "title": title,
      "wait": True,
      "wait_timeout": 120.0
    }
    return self._tool_call("source_add", payload)

  def query_notebook(self, prompt: str) -> dict:
    payload = {
      "notebook_id": self._notebook_id,
      "query": prompt
    }
    result = self._tool_call("notebook_query", payload)
    text = _extract_text(result.get("result"))
    return {"schema_version": "1.0", "result": {"text": text}}


_manager: NotebookManager | None = None


def get_manager() -> NotebookManager:
  global _manager
  if _manager is None:
    _manager = NotebookManager()
  return _manager
