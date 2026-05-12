import json
import re
from pathlib import Path

from forge.approval.manifest import load_manifest
from forge.loader import load_artifact_modules, extract_prompt


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "generated" / "manifest.json"
CATEGORY_MAP_PATH = ROOT / ".context" / "category_map.json"

OPENCODE_ROOT = Path.home() / ".config" / "opencode"
OPENCODE_SKILLS_DIR = OPENCODE_ROOT / "skills"
OPENCODE_AGENTS_DIR = OPENCODE_ROOT / "agents"


def _default_category_map() -> dict:
  return {
    "default": "system",
    "artifacts": {},
    "patterns": []
  }


def _load_category_map() -> dict:
  if not CATEGORY_MAP_PATH.exists():
    CATEGORY_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATEGORY_MAP_PATH.write_text(json.dumps(_default_category_map(), indent=2), encoding="utf-8")
  return json.loads(CATEGORY_MAP_PATH.read_text(encoding="utf-8"))


def _category_for(mapping: dict, kind: str, name: str) -> str:
  return _category_for_with_source(mapping, kind, name)[0]


def _category_for_with_source(mapping: dict, kind: str, name: str) -> tuple[str, str]:
  key = f"{kind}.{name}"
  artifacts = mapping.get("artifacts", {})
  if key in artifacts:
    return artifacts[key], "explicit"
  for rule in mapping.get("patterns", []):
    rule_kind = rule.get("kind")
    if rule_kind and rule_kind != kind:
      continue
    pattern = rule.get("match")
    if not pattern:
      continue
    try:
      if re.search(pattern, key, re.IGNORECASE):
        return rule.get("category", mapping.get("default", "system")), "pattern"
    except re.error:
      continue
  return mapping.get("default", "system"), "default"


def _title_category(value: str) -> str:
  parts = re.split(r"[^A-Za-z0-9]+", value.strip())
  parts = [p for p in parts if p]
  if not parts:
    return "System"
  return " ".join(p.capitalize() for p in parts)


def _slug_category(value: str) -> str:
  slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
  slug = re.sub(r"-+", "-", slug).strip("-")
  return slug or "system"


def _managed_frontmatter(description: str, name: str | None = None, mode: str | None = None) -> str:
  lines = ["---"]
  if name:
    lines.append(f"name: {name}")
  lines.append(f"description: {description}")
  if mode:
    lines.append(f"mode: {mode}")
  lines.append("metadata:")
  lines.append("  managed_by: forge")
  lines.append("---")
  return "\n".join(lines)


def _is_managed(content: str) -> bool:
  return "managed_by: forge" in content


def _build_section(title: str, prompt: str) -> str:
  return f"## {title}\n\n{prompt}\n"


def sync_opencode_mirror() -> dict:
  mapping = _load_category_map()
  manifest = load_manifest(MANIFEST_PATH)
  module_info = load_artifact_modules(MANIFEST_PATH)
  module_lookup = {(item.get("type"), item.get("name")): item for item in module_info}

  skills_by_category: dict[str, list[tuple[str, str]]] = {}
  agents_by_category: dict[str, list[tuple[str, str]]] = {}

  for item in manifest.get("artifacts", []):
    kind = item.get("type")
    name = item.get("name")
    if kind not in {"skill", "agent"} or not name:
      continue
    category = _category_for(mapping, kind, name)
    info = module_lookup.get((kind, name), {})
    module = info.get("module")
    prompt = None
    if module:
      prompt = extract_prompt(module, kind)
    if not prompt:
      prompt = item.get("summary", "")
    if kind == "skill":
      skills_by_category.setdefault(category, []).append((name, prompt))
    else:
      agents_by_category.setdefault(category, []).append((name, prompt))

  written = []
  written += _write_skill_files(skills_by_category, OPENCODE_SKILLS_DIR)
  written += _write_agent_files(agents_by_category, OPENCODE_AGENTS_DIR)
  return {
    "status": "ok",
    "written": written
  }


def list_categories() -> dict:
  mapping = _load_category_map()
  manifest = load_manifest(MANIFEST_PATH)
  categorized: dict[str, list[str]] = {}
  for item in manifest.get("artifacts", []):
    kind = item.get("type")
    name = item.get("name")
    if not kind or not name:
      continue
    category, source = _category_for_with_source(mapping, kind, name)
    categorized.setdefault(category, []).append(f"{kind}.{name} ({source})")
  return {
    "status": "ok",
    "categories": categorized
  }


def _write_skill_files(categories: dict[str, list[tuple[str, str]]], target_dir: Path) -> list[str]:
  target_dir.mkdir(parents=True, exist_ok=True)
  expected_dirs: set[Path] = set()
  written: list[str] = []

  for category, entries in sorted(categories.items()):
    title = _title_category(category)
    slug = _slug_category(category)
    skill_name = f"{slug}-skills"
    skill_dir = target_dir / skill_name
    expected_dirs.add(skill_dir)
    skill_dir.mkdir(parents=True, exist_ok=True)

    description = f"Aggregated {title.lower()} skills from forge generated artifacts."
    frontmatter = _managed_frontmatter(description, name=skill_name)

    sections = []
    for name, prompt in sorted(entries, key=lambda item: item[0].lower()):
      sections.append(_build_section(name, prompt))

    content = f"{frontmatter}\n\n# {title} Skills\n\n" + "\n".join(sections)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(content.strip() + "\n", encoding="utf-8")
    written.append(str(skill_path))

  for skill_dir in target_dir.iterdir():
    if not skill_dir.is_dir():
      continue
    if skill_dir in expected_dirs:
      continue
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.exists():
      continue
    try:
      content = skill_path.read_text(encoding="utf-8")
    except OSError:
      continue
    if _is_managed(content):
      for child in skill_dir.iterdir():
        if child.is_file():
          child.unlink()
      skill_dir.rmdir()

  return written


def _write_agent_files(categories: dict[str, list[tuple[str, str]]], target_dir: Path) -> list[str]:
  target_dir.mkdir(parents=True, exist_ok=True)
  expected_files: set[Path] = set()
  written: list[str] = []

  for category, entries in sorted(categories.items()):
    title = _title_category(category)
    filename = f"{title.replace(' ', '_')}_Agents.md"
    expected_path = target_dir / filename
    expected_files.add(expected_path)

    description = f"Aggregated {title.lower()} agents from forge generated artifacts."
    frontmatter = _managed_frontmatter(description, mode="all")

    sections = []
    for name, prompt in sorted(entries, key=lambda item: item[0].lower()):
      sections.append(_build_section(name, prompt))

    content = f"{frontmatter}\n\n# {title} Agents\n\n" + "\n".join(sections)
    expected_path.write_text(content.strip() + "\n", encoding="utf-8")
    written.append(str(expected_path))

  for path in target_dir.glob("*_Agents.md"):
    if path in expected_files:
      continue
    try:
      content = path.read_text(encoding="utf-8")
    except OSError:
      continue
    if _is_managed(content):
      path.unlink()

  return written
