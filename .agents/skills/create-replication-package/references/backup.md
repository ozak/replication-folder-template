# Backup, version control and synced drives

Read in Phase 0 (when choosing locations) and whenever the user versions the package with Git,
Git LFS, DVC or similar.

## Rule: caches, VCS internals and environments never live in a cloud-synced folder

Sync clients (Google Drive, Dropbox, OneDrive, iCloud) rename, evict ("online only"), deduplicate or
re-encode files, and they sync half-written files. Content-addressed stores are especially fragile:
Google Drive appended `.pdf` to extension-less DVC cache objects that contained PDFs, so DVC could no
longer find any PDF version (MS15875).

* DVC: `dvc cache dir --local ~/.dvc-cache/<project>` (outside any synced drive). For co-authors, a
  DVC remote on a server or bucket, not on a synced folder.
* Git: a synced working tree is usually fine, but keep large binaries out of `.git` (LFS/DVC) and
  never let two machines commit to the same synced `.git` at once.
* Conda/R environments, `renv` libraries, `__pycache__`, `.ipynb_checkpoints`: local only.

In Phase 0, when the target is in a synced drive and the user versions it with Git/DVC, say where
the DVC cache and environments must go instead.

## Byte-exact storage

Line-ending or encoding conversion changes data files (`.csv`, `.do`, `.tex`) and breaks hashes.
In the package repo set `* -text` in `.git/info/attributes` (or `.gitattributes`) so Git stores every
file as is.

## Integrity checks

After each commit that adds data: check that every entry of the DVC manifests (`*.dvc`, `dvc.lock`)
exists in the cache (`dvc status -c` / `dvc doctor`, or compare the md5 list with the cache folder).
Report missing objects immediately — they cannot be recovered later.

## Deleting

Never bulk-delete in the package. Copy what will be removed to `_migration/removed/<date>/` first,
then remove; keep `raw-data/` until the data-rebuilding steps have passed. Deletion in the original
folders is never allowed.
