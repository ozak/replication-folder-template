"""
Shared safety helpers for the create-replication-package scripts.

1. Source folders are READ-ONLY. Every script that writes refuses to write inside
   - any --project-root / --extra-root it was given, and
   - any folder listed in the environment variable REPLICATION_READONLY
     (os.pathsep-separated, e.g. export REPLICATION_READONLY="/path/to/Project:/path/to/Project-shared").
2. Cloud "online-only" files (Dropbox, Google Drive, OneDrive via macOS File Provider) are
   downloaded by the OS when opened. The first open can fail transiently (errno 35 EDEADLK
   "Resource deadlock avoided", EAGAIN, ETIMEDOUT) while the download starts — reads are retried.
   Reading never modifies the file: content and modification time stay the same.
"""
import errno
import os
import re
import sys
import time
from pathlib import Path

TRANSIENT = {errno.EDEADLK, errno.EAGAIN, errno.ETIMEDOUT, errno.EINTR, errno.EBUSY}
# On macOS the File Provider usually blocks the first open until the file is downloaded, so long
# waits are rarely useful; in a VM/sandbox the download never starts. Keep retries short.
DELAYS = (0.5,)


def readonly_roots(extra=()):
    roots = [Path(p).resolve() for p in os.environ.get("REPLICATION_READONLY", "").split(os.pathsep) if p.strip()]
    roots += [Path(p).resolve() for p in extra if p]
    return roots


def target_roots():
    return [Path(p).resolve() for p in os.environ.get("REPLICATION_TARGET", "").split(os.pathsep) if p.strip()]


def assert_writable(path, extra_roots=()):
    """Exit with an error if `path` lies inside a protected source folder.
    Paths inside REPLICATION_TARGET are always allowed — this is what lets the replication folder
    live inside a shared folder (e.g. <Project>-shared/<ID>-replication) whose other contents are
    read-only."""
    p = Path(path).resolve()
    if any(p == t or t in p.parents for t in target_roots()):
        return p
    for r in readonly_roots(extra_roots):
        if p == r or r in p.parents:
            sys.exit(f"REFUSED: {p} is inside the read-only source folder {r}. "
                     f"Write to the target replication folder (e.g. <target>/_migration/) instead.")
    return p


def read_bytes_retry(path):
    last = None
    for d in (0,) + DELAYS:
        if d:
            time.sleep(d)
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError as e:
            if e.errno not in TRANSIENT:
                raise
            last = e
    raise last


def read_text_retry(path, encoding="utf-8", errors="replace"):
    return read_bytes_retry(path).decode(encoding, errors=errors)


def probe(path):
    """(True, '') if the file can be read (downloading it if online-only), else (False, reason)."""
    try:
        last = None
        for d in (0,):   # probing: one attempt (a failed open of an online-only file is itself slow)
            if d:
                time.sleep(d)
            try:
                with open(path, "rb") as fh:
                    fh.read(1)
                return True, ""
            except OSError as e:
                if e.errno not in TRANSIENT:
                    return False, f"[Errno {e.errno}] {e.strerror}"
                last = e
        return False, f"[Errno {last.errno}] {last.strerror} (online-only file that this environment cannot download)"
    except Exception as e:  # pragma: no cover
        return False, str(e)


def check_locations(target, sources, shared=()):
    """Phase 0 check. Originals exist; the target is outside every original folder (except a
    `shared` folder, which may contain the target but is otherwise read-only); no original is inside
    the target; the target is new or empty."""
    t = Path(target).expanduser().resolve()
    problems = []
    for s in list(sources) + list(shared):
        p = Path(s).expanduser().resolve()
        if not p.is_dir():
            if s in shared:
                continue           # the shared folder may not exist yet — it will be created
            problems.append(f"original folder not found: {p}")
            continue
        if (t == p or p in t.parents) and s not in shared:
            problems.append(f"target {t} is inside the original folder {p}")
        if t in p.parents or t == p:
            problems.append(f"folder {p} is inside (or is) the target {t}")
    if t.exists() and any(x for x in t.iterdir() if x.name != ".DS_Store"):
        problems.append(f"target {t} already exists and is not empty — choose another name")
    return problems


CLOUD_MARKERS = [  # (regex on the path, label)
    (r"/Library/CloudStorage/Dropbox[^/]*", "Dropbox"),
    (r"/Dropbox(?: \([^)]*\))?", "Dropbox"),
    (r"/Library/CloudStorage/GoogleDrive-[^/]+/(?:My Drive|Shared drives/[^/]+)", "Google Drive"),
    (r"/Google Drive(?:/My Drive)?", "Google Drive"),
    (r"/Library/CloudStorage/OneDrive[^/]*", "OneDrive"),
    (r"/OneDrive[^/]*", "OneDrive"),
    (r"/Library/Mobile Documents/com~apple~CloudDocs", "iCloud"),
]


def cloud_root(path):
    import re
    s = str(path)
    for rx, label in CLOUD_MARKERS:
        m = re.search(rx, s)
        if m:
            return s[:m.end()], label, s[m.end():].lstrip("/")
    return None, None, None


def discover_cloud_roots(home=None):
    home = Path(home or Path.home())
    found = []
    cs = home / "Library" / "CloudStorage"
    if cs.is_dir():
        for d in sorted(cs.iterdir()):
            if d.name.startswith("GoogleDrive-"):
                for sub in ("My Drive",):
                    if (d / sub).is_dir():
                        found.append(str(d / sub))
            elif d.is_dir():
                found.append(str(d))
    for name in ("Dropbox", "Google Drive/My Drive", "OneDrive"):
        if (home / name).is_dir():
            found.append(str(home / name))
    return found


def no_spaces(name):
    """Package naming rule: whitespace in folder/file names becomes '-' (runs collapse to one)."""
    return re.sub(r"-{2,}", "-", re.sub(r"\s+", "-", str(name).strip()))


def suggest_targets(main_source, manuscript_id=None, cloud_roots=None):
    """Suggest where the replication package should live, following the convention
         original (working) folder :  <cloud A>/<path>/<Project>
         shared folder             :  <cloud B>/<path>/<Project>-shared       (shared with co-authors)
         replication package       :  <cloud B>/<path>/<Project>-shared/<ID>-replication
    i.e. the same relative path in a *different* synced drive (typically the original on Dropbox and
    the shared folder on Google Drive). Falls back to a sibling <Project>-shared folder."""
    src = Path(main_source).expanduser().resolve()
    project = no_spaces(src.name)  # "The Millennia of China" -> "The-Millennia-of-China"
    leaf = f"{no_spaces(manuscript_id)}-replication" if manuscript_id else f"{project}-replication"
    root, label, rel = cloud_root(src)
    out = []
    roots = cloud_roots if cloud_roots is not None else discover_cloud_roots()
    if root:
        rel_parent = str(Path(rel).parent) if rel and Path(rel).parent != Path(".") else ""
        for r in roots:
            r_label = cloud_root(r)[1] or Path(r).name
            if Path(r).resolve() == Path(root).resolve() or r_label == label:
                continue
            shared = Path(r) / rel_parent / f"{project}-shared"
            out.append((str(shared / leaf), str(shared), f"{project}-shared in {r_label} (mirrors the original's location)"))
    shared = src.parent / f"{project}-shared"
    out.append((str(shared / leaf), str(shared), f"sibling {project}-shared next to the original"))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Phase 0: suggest and validate where the replication package goes.")
    ap.add_argument("--sources", nargs="+", required=True, help="original folders (read-only); the first is the main project")
    ap.add_argument("--target", help="validate this target")
    ap.add_argument("--shared", nargs="*", default=[], help="shared folder(s) that contain the target (read-only except the target)")
    ap.add_argument("--suggest", action="store_true", help="print suggested targets")
    ap.add_argument("--id", default=None, help="manuscript ID, e.g. MS20230792")
    ap.add_argument("--cloud-roots", nargs="*", default=None, help="override detected synced-drive roots")
    a = ap.parse_args()
    if a.suggest:
        for i, (t, sh, why) in enumerate(suggest_targets(a.sources[0], a.id, a.cloud_roots), 1):
            ex = " (shared folder exists)" if Path(sh).is_dir() else ""
            spaced = Path(sh).with_name(Path(a.sources[0]).expanduser().name + "-shared")
            if spaced != Path(sh) and spaced.is_dir():
                ex += f"\n   note: '{spaced.name}' already exists — ask whether to use it (as an existing shared folder) or create '{Path(sh).name}'"
            print(f"{i}. {t}\n   {why}{ex}")
    if a.target:
        probs = check_locations(a.target, a.sources, a.shared)
        for p in probs:
            print("❌", p)
        if not probs:
            ro = [str(Path(s).expanduser().resolve()) for s in list(a.sources) + list(a.shared)]
            print("✅ target is valid: outside every original folder, new or empty")
            print(f'export REPLICATION_READONLY="{os.pathsep.join(ro)}" '
                  f'REPLICATION_TARGET="{Path(a.target).expanduser().resolve()}" PYTHONDONTWRITEBYTECODE=1')
        sys.exit(1 if probs else 0)
