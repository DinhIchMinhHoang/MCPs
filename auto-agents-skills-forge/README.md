# Auto Agents Skills Forge

Hybrid MCP forge for OpenCode agents, implemented fully in Python.

## Architecture

- **Forge Core (Python)**: Harvester, Synthesizer, Draft/Approve flow.
- **NotebookLM MCP (Python)**: MCP stdio server that shells out to `notebooklm-mcp`.
- **Artifacts**: Drafts in `draft/`, approved artifacts in `generated/` with `manifest.json`.

## Requirements

- Python 3.12.10
- `notebooklm-mcp-cli` installed (`pip install notebooklm-mcp-cli` or `uv tool install notebooklm-mcp-cli`)
- Windows PowerShell for `scripts/forge.ps1`

## Setup

From `auto-agents-skills-forge/forge-core`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Authenticate NotebookLM once:

```powershell
nlm login
```

## Run

Start the local MCP server (stdio) manually:

```powershell
..\scripts\forge.ps1 start-mcp
```

In a second terminal, generate drafts:

```powershell
..\scripts\forge.ps1 update
```

Approve a draft:

```powershell
..\scripts\forge.ps1 approve tool <name>
..\scripts\forge.ps1 approve skill <name>
..\scripts\forge.ps1 approve agent <name>
```

List drafts:

```powershell
..\scripts\forge.ps1 list drafts
```

Reject a draft:

```powershell
..\scripts\forge.ps1 reject <name>
```

## Notes

- MCP uses stdio transport and can be managed by OpenCode directly.
- All payloads require `schema_version: "1.0"`.
- HuggingFace cache is pinned to `D:\02_Data_Vault\.cache\huggingface`.
