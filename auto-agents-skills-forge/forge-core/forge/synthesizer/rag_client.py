from forge.harvester.session_store import save_session
from forge.synthesizer.notebook_manager import get_manager


def ingest_bundle(bundle: dict) -> None:
  save_session(bundle)
  get_manager().ingest_to_notebook(bundle)


def query_rag(bundle: dict) -> dict:
  prompt = (
    "Based on this session, propose new tools, skills, and agents. "
    "Format each line as: TOOL|<name>|<summary>, SKILL|<name>|<summary>, AGENT|<name>|<summary>."
  )
  return get_manager().query_notebook(prompt)
