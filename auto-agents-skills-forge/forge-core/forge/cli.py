import argparse

from forge.harvester.session_store import load_session
from forge.synthesizer.rag_client import query_rag
from forge.synthesizer.generator import generate_drafts
from forge.approval.promote import approve_artifact, reject_artifact, list_drafts


def _cmd_update(_args: argparse.Namespace) -> int:
  bundle = load_session()
  rag_output = query_rag(bundle)
  result = generate_drafts(rag_output)
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

  args = parser.parse_args(argv)
  if args.command == "update":
    return _cmd_update(args)
  if args.command == "approve":
    return _cmd_approve(args)
  if args.command == "reject":
    return _cmd_reject(args)
  if args.command == "list-drafts":
    return _cmd_list_drafts(args)

  parser.print_help()
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
