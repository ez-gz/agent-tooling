#!/usr/bin/env python3
"""
Regenerate manifest.json from SKILL.md frontmatter + git history.

Version = date of the last commit touching each skill directory (YYYY-MM-DD).
Bumping any file under skills/keep-alive/ automatically increments its version.
"""
import json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = ROOT / "skills"
MANIFEST = ROOT / "manifest.json"
RAW_BASE = "https://raw.githubusercontent.com/ez-gz/agent-tooling/main/skills"


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    result = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        kv = re.match(r"^([\w-]+):\s*(.*)", lines[i])
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val in (">", "|"):
                parts = []
                i += 1
                while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                    parts.append(lines[i].strip())
                    i += 1
                result[key] = " ".join(p for p in parts if p)
                continue
            else:
                result[key] = val.strip("\"'")
        i += 1
    return result


def git_last_date(path):
    """YYYY-MM-DD of the last commit that touched anything under path."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%as", "--", str(path)],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout.strip()
    return out or "0000-00-00"


def build_entry(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    fm = parse_frontmatter(skill_md.read_text())
    name = fm.get("name", "").strip()
    description = fm.get("description", "").strip()
    if not name or not description:
        return None

    sid = skill_dir.name
    entry = {
        "id": sid,
        "name": name,
        "version": git_last_date(skill_dir),
        "description": description,
    }

    if (skill_dir / "install.sh").exists():
        entry["install_sh"] = f"curl -fsSL {RAW_BASE}/{sid}/install.sh | bash"

    return entry


def main():
    if not SKILLS_DIR.exists():
        print("skills/ directory not found")
        return

    skills = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        entry = build_entry(d)
        if entry:
            skills.append(entry)

    manifest = {"version": 1, "skills": skills}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"manifest.json: {len(skills)} skill(s)")
    for s in skills:
        install = "install.sh" if "install_sh" in s else "SKILL.md only"
        print(f"  {s['id']:30s}  {s['version']}  ({install})")


main()
