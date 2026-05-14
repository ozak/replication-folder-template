#!/usr/bin/env python3
"""
Export a conda/mamba environment as a clean, portable environment.yml.

Strategy:
- Use `mamba env export --from-history` to identify top-level (explicitly installed) packages.
- Use `mamba env export` (full) to get pinned versions for those packages.
- Keep the pip section from the full export as-is (those are genuinely pip-installed).
- Remove from pip any package already present in the conda section (no duplicates).
- Strip the `prefix:` line (machine-specific path).

Usage:
    python scripts/export_env.py -n <env-name> -o environment.yml [--name <slug>]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running {' '.join(cmd)}:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def parse_yaml_deps(text):
    """Return (conda_deps_list, pip_deps_list, channels, name) from env export yaml text."""
    lines = text.splitlines()
    name = ""
    channels = []
    conda_deps = []
    pip_deps = []
    in_deps = False
    in_pip = False

    for line in lines:
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("channels:"):
            in_deps = False
        elif re.match(r"^  - ", line) and not in_deps:
            channels.append(line.strip().lstrip("- "))
        elif line.startswith("dependencies:"):
            in_deps = True
            in_pip = False
        elif in_deps and re.match(r"^  - pip:", line):
            in_pip = True
        elif in_deps and in_pip and re.match(r"^    - ", line):
            pip_deps.append(line.strip().lstrip("- "))
        elif in_deps and re.match(r"^  - ", line) and not in_pip:
            conda_deps.append(line.strip().lstrip("- "))
        elif line.startswith("prefix:"):
            continue
        elif in_deps and not line.startswith(" "):
            in_deps = False

    return name, channels, conda_deps, pip_deps


def pkg_name(dep_str):
    """Extract package name from a versioned dep string like 'python=3.11.9=...' or 'python=3.11'."""
    return re.split(r"[=><!@\s]", dep_str)[0].lower()


def main():
    parser = argparse.ArgumentParser(description="Export conda env as clean environment.yml")
    parser.add_argument("-n", "--name", required=True, help="Conda environment name to export")
    parser.add_argument("-o", "--output", type=Path, default=Path("environment.yml"),
                        help="Output file (default: environment.yml)")
    parser.add_argument("--slug", default=None,
                        help="Override the 'name:' field in the output yml (paper slug)")
    args = parser.parse_args()

    print(f"Exporting environment: {args.name}", file=sys.stderr)

    # Full export — has pinned versions for conda deps + pip section
    full_text = run(["mamba", "env", "export", "-n", args.name])
    _, channels, full_conda, full_pip = parse_yaml_deps(full_text)

    # From-history export — top-level packages only, without transitive deps
    hist_text = run(["mamba", "env", "export", "--from-history", "-n", args.name])
    _, _, hist_conda, hist_pip = parse_yaml_deps(hist_text)

    # Build a lookup: name → versioned string from full export
    full_conda_map = {pkg_name(d): d for d in full_conda}

    # For each top-level conda package, find its pinned version from full export.
    # Keep only the package=version part (drop the build string after the second =).
    result_conda = []
    for dep in hist_conda:
        name_only = pkg_name(dep)
        if name_only in full_conda_map:
            versioned = full_conda_map[name_only]
            # Trim build strings: keep only up to second '=' segment
            parts = versioned.split("=")
            if len(parts) >= 2:
                versioned = f"{parts[0]}={parts[1]}"
            result_conda.append(versioned)
        else:
            result_conda.append(dep)

    # Pip section: use from-history pip if available, else full pip.
    # Either way, remove any package that's already in the conda section.
    conda_names = {pkg_name(d) for d in result_conda}
    pip_source = hist_pip if hist_pip else full_pip
    result_pip = [p for p in pip_source if pkg_name(p) not in conda_names]

    # Write output
    slug = args.slug or args.name
    lines = [f"name: {slug}", "channels:"]
    for ch in channels:
        lines.append(f"  - {ch}")
    lines.append("dependencies:")
    for dep in sorted(result_conda):
        lines.append(f"  - {dep}")
    if result_pip:
        lines.append("  - pip:")
        for p in result_pip:
            lines.append(f"    - {p}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ environment.yml written to {args.output} ({len(result_conda)} conda, {len(result_pip)} pip packages)")


if __name__ == "__main__":
    main()
