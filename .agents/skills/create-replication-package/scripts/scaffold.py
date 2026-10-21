#!/usr/bin/env python3
"""
Create a new replication folder from the template — the user never clones anything.

Usage:
    python scaffold.py --target "<Project>-shared/<ID>-replication" --slug <paper-slug> \
        --info draft-info.json [--no-r] [--no-stata] [--from bundled|github|<local template path>]

Template source (default `bundled`): the copy shipped inside this skill at
SKILL_DIR/assets/template/, so the scripts and the template always match and no network is
needed. `--from github` clones https://github.com/ozak/replication-folder-template (latest);
a path uses a local clone. Template-development files (.git, .claude/, .agents/, CLAUDE.md,
*.code-workspace, the repo README) are never copied.

Then it:
  * removes components the paper does not use (--no-r: environment.R, progs/R;
    --no-stata: setup.do, progs/Stata) and the Stata placeholder notebook;
  * sets the environment name (environment.yml `name:`, create_env.sh ENV_NAME) to --slug;
  * creates the standard folders (raw-data, data, scratch_data, html, graphs|tables/paper|appendix,
    _migration);
  * copies the confirmed paper/author information (--info, see project_info.py) to
    <target>/replication-info.json and fills the template tokens (title, all authors, citation,
    compute specs, logos) from it; lists any token still unfilled.
Refuses to write into a non-empty folder or into a read-only source (REPLICATION_READONLY).
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
BUNDLED = SKILL_DIR / "assets" / "template"
IGNORE = shutil.ignore_patterns(".git", ".claude", ".agents", "CLAUDE.md", "*.code-workspace", ".DS_Store",
                                "__pycache__", ".ipynb_checkpoints", ".replication_defaults.yml",
                                ".replication_defaults.yml.example")
STD_DIRS = ["_migration", "replication-package/raw-data", "replication-package/data", "replication-package/scratch_data",
            "replication-package/html", "replication-package/graphs/paper", "replication-package/graphs/appendix",
            "replication-package/tables/paper", "replication-package/tables/appendix"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True)
    ap.add_argument("--slug", required=True, help="environment / paper slug, e.g. country-stability")
    ap.add_argument("--from", dest="src", default="bundled")
    ap.add_argument("--no-r", action="store_true")
    ap.add_argument("--no-stata", action="store_true")
    ap.add_argument("--info", default=None, help="confirmed paper/author info (project_info.py); copied into the target")
    a = ap.parse_args()

    t = assert_writable(Path(a.target).expanduser())
    if t.exists() and any(x for x in t.iterdir() if x.name != ".DS_Store"):
        sys.exit(f"REFUSED: {t} exists and is not empty")

    tmp = None
    if a.src == "bundled":
        src = BUNDLED
    elif a.src == "github":
        tmp = Path(tempfile.mkdtemp())
        r = subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ozak/replication-folder-template",
                            str(tmp / "tpl")], capture_output=True, text=True)
        if r.returncode:
            print(f"git clone failed ({r.stderr.strip()[:200]}); using the bundled template", file=sys.stderr)
            src = BUNDLED
        else:
            src = tmp / "tpl"
    else:
        src = Path(a.src).expanduser()
    if not (src / "replication-package").is_dir():
        sys.exit(f"template not found at {src}")

    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, t, ignore=IGNORE, dirs_exist_ok=True)
    readme = t / "README.md"  # repo README, not the package README
    if readme.exists() and (t / "replication-package" / "README.md").exists():
        readme.unlink()
    for rel in ["replication-package/progs/Stata/Stata-Notebook.ipynb"] + \
               (["replication-package/environment.R", "replication-package/progs/R"] if a.no_r else []) + \
               (["replication-package/setup.do", "replication-package/progs/Stata"] if a.no_stata else []):
        p = t / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    for d in STD_DIRS:
        (t / d).mkdir(parents=True, exist_ok=True)

    env = t / "replication-package" / "environment.yml"
    if env.exists():
        env.write_text(re.sub(r"^name:.*$", f"name: {a.slug}", env.read_text(), count=1, flags=re.M))
    sh = t / "replication-package" / "create_env.sh"
    if sh.exists():
        sh.write_text(re.sub(r'ENV_NAME="[^"]*"', f'ENV_NAME="{a.slug}"', sh.read_text(), count=1))
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"✅ created {t} from {'bundled template' if src == BUNDLED else src}")

    if a.info:
        shutil.copyfile(Path(a.info).expanduser(), t / "replication-info.json")
    cmd = [sys.executable, "-B", str(Path(__file__).resolve().parent / "apply_defaults.py"), str(t)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if r.returncode:
        print("⚠️  Template tokens not filled yet: build replication-info.json with project_info.py, confirm the "
              "authors with the user, then run apply_defaults.py on the target.")


if __name__ == "__main__":
    main()
