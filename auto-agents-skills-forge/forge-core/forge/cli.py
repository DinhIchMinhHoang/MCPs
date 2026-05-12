import argparse
import json
from pathlib import Path

from forge.harvester.session_store import load_session
from forge.synthesizer.rag_client import query_rag
from forge.synthesizer.generator import generate_drafts
from forge.approval.promote import approve_artifact, reject_artifact, list_drafts, auto_promote
from forge.loader import load_generated, list_generated, describe_generated, invoke_generated
from forge.opencode_mirror import sync_opencode_mirror


def _cmd_update(_args: argparse.Namespace) -> int:
  bundle = load_session()
  rag_output = query_rag(bundle)
  result = generate_drafts(rag_output)
  promotion = auto_promote()
  print(json.dumps({"drafts": result, "auto_promoted": promotion}, indent=2, default=str))
  return 0


def _cmd_approve(args: argparse.Namespace) -> int:
  approve_artifact(args.kind, args.name)
  return 0


def _cmd_reject(args: argparse.Namespace) -> int:
  reject_artifact(args.name)
  return 0


def _cmd_list_drafts(_args: argparse.Namespace) -> int:
  list_drafts()
  return 0


def _cmd_load_generated(_args: argparse.Namespace) -> int:
  manifest_path = Path(__file__).resolve().parents[2] / "generated" / "manifest.json"
  results = load_generated(manifest_path)
  for result in results:
    status = result.get("status", "unknown")
    name = result.get("name", "")
    kind = result.get("type", "artifact")
    reason = result.get("reason")
    if reason:
      print(f"{kind} {name} {status} {reason}")
    else:
      print(f"{kind} {name} {status}")
  return 0


def _cmd_describe_generated(args: argparse.Namespace) -> int:
  manifest_path = Path(__file__).resolve().parents[2] / "generated" / "manifest.json"
  result = describe_generated(manifest_path, args.kind, args.name)
  print(json.dumps(result, indent=2, default=str))
  return 0


def _cmd_invoke_generated(args: argparse.Namespace) -> int:
  manifest_path = Path(__file__).resolve().parents[2] / "generated" / "manifest.json"
  payload = json.loads(args.payload) if args.payload else {}
  result = invoke_generated(manifest_path, args.kind, args.name, payload)
  print(json.dumps(result, indent=2, default=str))
  return 0


def _cmd_list_generated(_args: argparse.Namespace) -> int:
  manifest_path = Path(__file__).resolve().parents[2] / "generated" / "manifest.json"
  results = list_generated(manifest_path)
  for r in results:
    kind = r.get("type", "artifact")
    name = r.get("name", "")
    status = r.get("status", "unknown")
    print(f"{kind} {name} {status}")
  return 0


def _cmd_sync_opencode(_args: argparse.Namespace) -> int:
  result = sync_opencode_mirror()
  print(json.dumps(result, indent=2, default=str))
  return 0


def _cmd_list_categories(_args: argparse.Namespace) -> int:
  from forge.opencode_mirror import list_categories
  result = list_categories()
  print(json.dumps(result, indent=2, default=str))
  return 0


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(prog="forge")
  sub = parser.add_subparsers(dest="command", required=True)

  sub.add_parser("update")

  approve = sub.add_parser("approve")
  approve.add_argument("kind", choices=["tool", "skill", "agent"])
  approve.add_argument("name")

  reject = sub.add_parser("reject")
  reject.add_argument("name")

  sub.add_parser("list-drafts")
  sub.add_parser("load-generated")
  sub.add_parser("list-generated")
  sub.add_parser("sync-opencode")
  sub.add_parser("list-categories")

  describe = sub.add_parser("describe")
  describe.add_argument("kind", choices=["tool", "skill", "agent"])
  describe.add_argument("name")

  invoke = sub.add_parser("invoke")
  invoke.add_argument("kind", choices=["tool"])
  invoke.add_argument("name")
  invoke.add_argument("--payload", default=None)

  args = parser.parse_args(argv)
  if args.command == "update":
    return _cmd_update(args)
  if args.command == "approve":
    return _cmd_approve(args)
  if args.command == "reject":
    return _cmd_reject(args)
  if args.command == "list-drafts":
    return _cmd_list_drafts(args)
  if args.command == "load-generated":
    return _cmd_load_generated(args)
  if args.command == "list-generated":
    return _cmd_list_generated(args)
  if args.command == "describe":
    return _cmd_describe_generated(args)
  if args.command == "invoke":
    return _cmd_invoke_generated(args)
  if args.command == "sync-opencode":
    return _cmd_sync_opencode(args)
  if args.command == "list-categories":
    return _cmd_list_categories(args)

  parser.print_help()
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
