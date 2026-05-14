#!/usr/bin/env python3
"""
Substitute {{placeholder}} tokens in replication package files using values
from a .replication_defaults.yml file.

Usage:
    python scripts/apply_defaults.py <target-dir> [--defaults <path>]

Searches for .replication_defaults.yml starting from the target directory,
then walking up to the user's home directory. Replaces all {{key}} tokens
in text files under target-dir with the corresponding values.

If no defaults file is found, prints a warning and lists the unfilled tokens.
"""
import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    # Fallback: minimal YAML parser for simple key: "value" files
    def yaml_load(text):
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                val = val.strip().strip('"').strip("'")
                result[key.strip()] = val
        return result
    class yaml:
        @staticmethod
        def safe_load(text):
            return yaml_load(text)


SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg", ".gif",
    ".zip", ".gz", ".tar", ".pkl", ".dta", ".parquet",
    ".pyc", ".so", ".skill",
}

TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")


def find_defaults(start: Path) -> Path | None:
    """Walk up from start toward home looking for .replication_defaults.yml."""
    home = Path.home()
    current = start.resolve()
    while True:
        candidate = current / ".replication_defaults.yml"
        if candidate.exists():
            return candidate
        if current == home or current == current.parent:
            break
        current = current.parent
    # Also check home directly
    candidate = home / ".replication_defaults.yml"
    return candidate if candidate.exists() else None


def apply_to_file(path: Path, defaults: dict) -> int:
    """Substitute tokens in a single file. Returns number of substitutions made."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0

    tokens_found = set(TOKEN_RE.findall(text))
    if not tokens_found:
        return 0

    count = 0
    for token in tokens_found:
        if token in defaults:
            text = text.replace(f"{{{{{token}}}}}", defaults[token])
            count += 1

    path.write_text(text, encoding="utf-8")
    return count


def main():
    parser = argparse.ArgumentParser(description="Apply replication defaults to template files")
    parser.add_argument("target_dir", type=Path, help="Directory to process")
    parser.add_argument("--defaults", type=Path, default=None,
                        help="Path to .replication_defaults.yml (auto-detected if omitted)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without writing")
    args = parser.parse_args()

    if not args.target_dir.exists():
        print(f"Error: target directory not found: {args.target_dir}", file=sys.stderr)
        sys.exit(1)

    defaults_path = args.defaults or find_defaults(args.target_dir)
    if not defaults_path:
        print("⚠️  No .replication_defaults.yml found. Copy .replication_defaults.yml.example,",
              "fill in your details, and re-run.", file=sys.stderr)
        # Still scan for unfilled tokens so the user knows what's needed
        all_tokens = set()
        for f in args.target_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() not in SKIP_EXTENSIONS:
                try:
                    all_tokens.update(TOKEN_RE.findall(f.read_text(encoding="utf-8", errors="replace")))
                except Exception:
                    pass
        if all_tokens:
            print(f"Unfilled tokens found: {sorted(all_tokens)}", file=sys.stderr)
        sys.exit(1)

    defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
    print(f"Using defaults from: {defaults_path}")

    total = 0
    for f in sorted(args.target_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if ".git" in f.parts:
            continue

        if args.dry_run:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tokens = set(TOKEN_RE.findall(text))
                if tokens:
                    print(f"  {f.relative_to(args.target_dir)}: {sorted(tokens)}")
            except Exception:
                pass
        else:
            n = apply_to_file(f, defaults)
            if n:
                print(f"  {f.relative_to(args.target_dir)}: {n} substitution(s)")
                total += n

    if not args.dry_run:
        print(f"✅ {total} total substitution(s) applied from {defaults_path.name}")


if __name__ == "__main__":
    main()
