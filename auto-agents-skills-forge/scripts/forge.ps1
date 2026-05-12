param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$Command,
  [Parameter(Position = 1)]
  [string]$Subcommand,
  [Parameter(Position = 2)]
  [string]$Name
)

$root = Split-Path -Parent $PSScriptRoot
$forgeCore = Join-Path $root "forge-core"
$venvPath = Join-Path $forgeCore ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
  Write-Error "Python venv not found at $venvPath. Create it with: python -m venv .venv"
  exit 1
}

$cli = Join-Path $forgeCore "forge\cli.py"

switch ($Command) {
  "update" {
    & $pythonExe $cli update
  }
  "start-mcp" {
    & $pythonExe -m forge.mcp.server
  }
  "approve" {
    if (-not $Subcommand -or -not $Name) {
      Write-Error "Usage: forge approve <tool|skill|agent> <name>"
      exit 1
    }
    & $pythonExe $cli approve $Subcommand $Name
  }
  "reject" {
    if (-not $Subcommand) {
      Write-Error "Usage: forge reject <name>"
      exit 1
    }
    & $pythonExe $cli reject $Subcommand
  }
  "list" {
    if ($Subcommand -ne "drafts") {
      Write-Error "Usage: forge list drafts"
      exit 1
    }
    & $pythonExe $cli list-drafts
  }
  Default {
    Write-Error "Unknown command. Supported: start-mcp, update, approve, reject, list drafts"
    exit 1
  }
}
