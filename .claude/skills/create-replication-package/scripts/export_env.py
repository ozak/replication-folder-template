#!/usr/bin/env python3
"""
Export the conda/mamba environment the authors used as a clean, portable environment.yml.

Usage:
    python export_env.py -n <env-name> -o environment.yml --slug <paper-slug>
    python export_env.py --prefix <path/to/envs/name> -o environment.yml --slug <paper-slug>

Strategy (same result either way):
- Top-level packages only: the specs the user explicitly requested (`--from-history`, or
  conda-meta/history when reading the env folder directly), each pinned to the installed version
  (`name=version`, no build strings — portable across macOS/Linux).
- pip section: packages installed with pip (pip export / dist-info INSTALLER=pip), pinned
  (`name==version`), minus anything already in the conda section.
- Channels from the installed packages (conda-forge first); no `prefix:` line.
`--prefix` reads the environment folder directly, so it works without conda on PATH (e.g. from a
VM where the user's Mac folders are mounted) — the agent must have read access to that folder.
--add-missing NAME... appends packages the code imports but the env lacks (see detect_envs.py),
marked with a comment so the authors can confirm.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safety import assert_writable  # noqa: E402


# infrastructure / platform-specific packages that should not be pinned in a portable env
INFRA = {"ca-certificates", "certifi", "openssl", "tzdata", "libblas", "libcblas", "liblapack", "blas", "python_abi"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Error running {' '.join(cmd)}:\n{r.stderr}")
    return r.stdout


def parse_yaml_deps(text):
    name, channels, conda_deps, pip_deps = "", [], [], []
    section = None
    for line in text.splitlines():
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("channels:"):
            section = "ch"
        elif line.startswith("dependencies:"):
            section = "deps"
        elif line.startswith("prefix:") or (line and not line.startswith(" ")):
            section = None
        elif section == "ch" and re.match(r"^\s+- ", line):
            channels.append(line.strip()[2:].strip())
        elif section == "deps" and re.match(r"^  - pip:", line):
            section = "pip"
        elif section == "deps" and re.match(r"^  - ", line):
            conda_deps.append(line.strip()[2:].strip())
        elif section == "pip" and re.match(r"^    - ", line):
            pip_deps.append(line.strip()[2:].strip())
        elif section == "pip" and re.match(r"^  - ", line):
            section = "deps"
            conda_deps.append(line.strip()[2:].strip())
    return name, channels, conda_deps, pip_deps


def pkg_name(dep):
    return re.split(r"[=><!@\s\[]", dep.split("::")[-1])[0].lower()


def from_command(env):
    exe = next((x for x in ("mamba", "conda", "micromamba") if shutil.which(x)), None)
    if not exe:
        return None
    full = run([exe, "env", "export", "-n", env])
    hist = run([exe, "env", "export", "--from-history", "-n", env])
    _, channels, full_conda, full_pip = parse_yaml_deps(full)
    _, _, hist_conda, _ = parse_yaml_deps(hist)
    fmap = {pkg_name(d): d for d in full_conda}
    conda = []
    for d in hist_conda:
        v = fmap.get(pkg_name(d), d).split("=")
        conda.append(f"{v[0]}={v[1]}" if len(v) >= 2 else d)
    return channels, conda, full_pip


def from_prefix(prefix):
    import detect_envs
    pk, _, _ = detect_envs.env_packages(prefix)
    requested_specs = detect_envs.requested_specs
    req = requested_specs(prefix)
    if not req:
        sys.exit(f"no conda-meta/history in {prefix}: cannot tell top-level packages apart")
    conda, chans = [], []
    for name in sorted(n for n in req if n not in INFRA):
        if name in pk and pk[name][2] == "conda":
            conda.append(f"{name}={pk[name][0]}")
            if pk[name][1] and pk[name][1] not in chans:
                chans.append(pk[name][1])
        else:
            conda.append(req[name].split("::")[-1])
    pip = sorted(f"{n}=={v[0]}" for n, v in pk.items() if v[2] == "pip" and n not in detect_envs.PIP_REQUIRES)
    chans = sorted(chans, key=lambda c: (c != "conda-forge", c)) or ["conda-forge"]
    return chans, conda, pip


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--name", default=None, help="conda environment name")
    ap.add_argument("--prefix", default=None, help="environment folder (reads conda-meta directly)")
    ap.add_argument("-o", "--output", type=Path, default=Path("environment.yml"))
    ap.add_argument("--slug", default=None, help="'name:' of the exported env (paper slug)")
    ap.add_argument("--add-missing", nargs="*", default=[], help="packages to add (imports the env lacks)")
    a = ap.parse_args()
    if not a.name and not a.prefix:
        sys.exit("give -n <env> or --prefix <env folder>")
    got = None
    if a.name and not a.prefix:
        got = from_command(a.name)
        if got is None:
            sys.exit("no mamba/conda on PATH: pass --prefix <base>/envs/<name> (see detect_envs.py)")
    else:
        got = from_prefix(Path(a.prefix).expanduser())
    channels, conda, pip = got
    names = {pkg_name(d) for d in conda}
    pip = [p for p in pip if pkg_name(p) not in names]
    slug = a.slug or a.name or Path(a.prefix).name
    lines = [f"name: {slug}", "channels:"] + [f"  - {c}" for c in channels] + ["dependencies:"]
    lines += [f"  - {d}" for d in sorted(conda, key=str.lower)]
    for m in a.add_missing:
        lines.append(f"  - {m}  # added: imported by the code but not in the authors' env — confirm")
    if pip:
        lines.append("  - pip:")
        lines += [f"    - {p}" for p in pip]
    assert_writable(a.output)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ {a.output}: {len(conda)} conda + {len(pip)} pip packages (env {a.name or a.prefix} → name '{slug}')")


if __name__ == "__main__":
    main()
