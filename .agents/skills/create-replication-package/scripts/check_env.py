#!/usr/bin/env python3
"""
Check that environment files resolve on every target platform — without installing anything.

Usage:
    python check_env.py <pkg>/environment.yml [<pkg>/environment-R.yml] [--platforms linux-64 osx-arm64 win-64]
        [--solver mamba|micromamba|conda] [--pip] [--report _migration/env-check.md]

For each file and platform it runs a dry-run solve with CONDA_SUBDIR / --platform and virtual-package
overrides (glibc 2.28 + Linux 5.14 for linux-64; macOS 13 for osx-*), using the first solver found
(mamba, micromamba, conda). Each solve takes about a minute. On failure it shows the solver's
explanation, names the pinned packages involved, and suggests what to relax first:
system libraries (should not be pinned at all) → minor-pinned packages → exact pins (result-computing
packages: never relax without asking the authors).
--pip also checks that every pinned pip requirement exists on PyPI (`pip index versions`, needs network).
Exit code 1 if any solve fails.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable  # noqa: E402

try:
    from export_env import PIN_EXACT, is_system, norm  # noqa: E402
except Exception:  # pragma: no cover
    PIN_EXACT, is_system, norm = set(), (lambda n: False), (lambda n: n.lower())

OVERRIDES = {"linux": {"CONDA_OVERRIDE_GLIBC": "2.28", "CONDA_OVERRIDE_LINUX": "5.14"},
             "osx": {"CONDA_OVERRIDE_OSX": "13.0"}, "win": {}}


def parse(path):
    conda, pip, sec = [], [], None
    for line in Path(path).read_text().splitlines():
        s = line.split("#")[0].rstrip()
        if s.startswith("dependencies:"):
            sec = "deps"
        elif re.match(r"^\s+- pip:\s*$", s):
            sec = "pip"
        elif sec == "pip" and re.match(r"^\s{4,}- ", s):
            pip.append(s.strip()[2:].strip())
        elif sec in ("deps", "pip") and re.match(r"^\s{2}- ", s):
            sec = "deps"
            conda.append(s.strip()[2:].strip())
    return conda, pip


def solver(pref):
    for exe in ([pref] if pref else ["mamba", "micromamba", "conda"]):
        if exe and shutil.which(exe):
            return exe
    return None


def run(cmd, env):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
    except subprocess.TimeoutExpired:
        return 1, "solver timed out after 30 min"
    return r.returncode, (r.stdout + "\n" + r.stderr).strip()


def solve(exe, yml, platform, workdir):
    env = dict(os.environ, CONDA_SUBDIR=platform, **OVERRIDES[platform.split("-")[0]])
    env.setdefault("MAMBA_ROOT_PREFIX", str(Path(workdir) / "root"))
    prefix = str(Path(workdir) / f"dry-{platform}")
    # conda does not solve the pip section: check only the conda packages
    conda, _ = parse(yml)
    chans = re.findall(r"^\s+- (\S+)\s*$", Path(yml).read_text().split("dependencies:")[0], re.M) or ["conda-forge"]
    tmp = Path(workdir) / f"{Path(yml).stem}-{platform}.yml"
    tmp.write_text("channels:\n" + "".join(f"  - {c}\n" for c in chans) + "dependencies:\n" + "".join(f"  - {c}\n" for c in conda))
    base = Path(exe).name
    if base in ("micromamba", "mamba"):      # mamba 2 has the micromamba interface
        code, out = run([exe, "create", "-y", "--dry-run", "-p", prefix, "-f", str(tmp), "--platform", platform], env)
        if base == "micromamba" or not (code and re.search(r"unrecognized|no such option|unknown", out, re.I)):
            return code == 0, out
    code, out = run([exe, "env", "create", "--dry-run", "-p", prefix, "-f", str(tmp)], env)   # conda / mamba 1
    return code == 0, out


def classify(spec):
    name = re.split(r"[=<>!\s]", spec)[0]
    if "=" not in spec:
        return name, "unpinned"
    if is_system(name.lower()):
        return name, "system (should not be pinned)"
    if norm(name) in {norm(x) for x in PIN_EXACT}:
        return name, "exact (computes results — ask before relaxing)"
    return name, "minor/other (relax first)"


def check_pip(pins):
    bad = []
    for p in pins:
        m = re.match(r"([A-Za-z0-9_.-]+)==([\w.]+)", p)
        if not m:
            continue
        r = subprocess.run([sys.executable, "-m", "pip", "index", "versions", m.group(1)], capture_output=True, text=True)
        if r.returncode or m.group(2) not in re.findall(r"[\w.]+", r.stdout.split("Available versions:")[-1]):
            bad.append(p)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--platforms", nargs="+", default=["linux-64", "osx-arm64"])
    ap.add_argument("--solver", default=None)
    ap.add_argument("--pip", action="store_true")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    exe = solver(a.solver)
    if not exe:
        sys.exit("no mamba, micromamba or conda found — install miniforge (ask the user first) or run this on a machine that has one")
    ok_all, L = True, [f"# Environment check ({Path(exe).name})", ""]
    with tempfile.TemporaryDirectory() as wd:
        for f in a.files:
            conda, pip = parse(f)
            for plat in a.platforms:
                ok, out = solve(exe, f, plat, wd)
                ok_all &= ok
                head = f"- {'✅' if ok else '❌'} `{Path(f).name}` on **{plat}**"
                L.append(head)
                print(head, flush=True)
                if not ok:
                    tail = "\n".join(out.splitlines()[-40:])
                    involved = [c for c in conda if re.search(r"\b" + re.escape(re.split(r"[=<>!\s]", c)[0]) + r"\b", out, re.I)]
                    block = ["", "  ```", *("  " + x for x in tail.splitlines()), "  ```", "  Pinned packages named by the solver:"]
                    block += [f"  - `{c}` — {classify(c)[1]}" for c in involved] or ["  - (none recognized — read the message above)"]
                    L += block + [""]
                    print("\n".join(block), flush=True)
            if a.pip and pip:
                bad = check_pip(pip)
                L.append(f"- {'✅' if not bad else '❌'} pip pins in `{Path(f).name}` exist on PyPI" +
                         (f": missing {', '.join(bad)}" if bad else ""))
                ok_all &= not bad
    text = "\n".join(L) + "\n"
    if a.report:
        assert_writable(a.report)
        Path(a.report).write_text(text)
    print(("✅ all environments resolve" if ok_all else "❌ some environments do not resolve") +
          (f" — report: {a.report}" if a.report else ""))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
