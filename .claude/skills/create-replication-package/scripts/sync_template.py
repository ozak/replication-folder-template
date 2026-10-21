#!/usr/bin/env python3
"""
For template maintainers: refresh the template copy bundled with the skill
(SKILL_DIR/assets/template/) from the template repository it lives in.

Usage (from anywhere inside the replication-folder-template repo):
    python3 .claude/skills/create-replication-package/scripts/sync_template.py
    python3 .agents/skills/create-replication-package/scripts/sync_template.py

Run it after editing 1-paper/, 2-appendix/, replication-package/ or replication-zip.ipynb so
packages created by the skill use the new template. Users of the skill never need this.
"""
import shutil
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO = SKILL_DIR.parents[2]          # <repo>/.claude/skills/<skill>  ->  <repo>
DEST = SKILL_DIR / "assets" / "template"
ITEMS = ["1-paper", "2-appendix", "replication-package", "replication-zip.ipynb",
         "LICENSE.txt", "LicenseCC-BY-SA-4.0.txt", ".gitignore", ".gitattributes"]
IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", ".ipynb_checkpoints", "*.pyc")

if not (REPO / "replication-package").is_dir():
    raise SystemExit(f"{REPO} does not look like the template repository")
if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
for it in ITEMS:
    s = REPO / it
    if s.is_dir():
        shutil.copytree(s, DEST / it, ignore=IGNORE)
    elif s.exists():
        shutil.copy2(s, DEST / it)
n = sum(1 for p in DEST.rglob("*") if p.is_file())
print(f"✅ bundled template refreshed: {n} files in {DEST}")
