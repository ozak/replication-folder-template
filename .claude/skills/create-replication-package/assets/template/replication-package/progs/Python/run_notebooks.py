"""
Runs the package's notebooks for index.ipynb — one at a time or in parallel — robustly.

In index.ipynb (which runs from replication-package/):

    import sys; sys.path.insert(0, "./progs/Python")
    from run_notebooks import Runner
    runner = Runner(parallel=False)          # True: register the steps, then runner.run_all() at the end
    ...
    runner.step("progs/Python/Clean-Data.ipynb")
    runner.step("progs/Stata/Regressions.ipynb", after=["Clean-Data"])
    ...
    runner.run_all()                         # parallel mode only; prints a summary in both modes

From a shell / scheduler (same rules):
    python progs/Python/run_notebooks.py progs/Python/A.ipynb progs/Stata/B.ipynb:after=A --parallel 4

What it guarantees
  * Every notebook is executed in its own folder (relative paths ../../data/...), with no timeout,
    and is SAVED and exported to html/<name>.html even when it fails, so the HTML shows where it stopped.
  * Limited resources have their own limits: `max_parallel` notebooks in total, and per resource
    (`limits={"stata": 2, "gurobi": 1}`). A notebook uses "stata" when it runs Stata (pystata:
    `import stata_init` / %%stata cells); other resources are given with `step(..., uses={"gpu": 1})`.
    The Stata limit defaults to min(licence seats read from the Stata banner, cores // cores per session).
  * "Could not start" is not "failed": an error in a notebook's first code cell (e.g. `import stata_init`
    when no licence seat is free) or a kernel that dies at start-up is retried every `retry_every`
    seconds for up to `retry_for` seconds; the notebook keeps its place. Errors in later cells are real
    failures.
  * Dependencies: `after=[...]` waits for the named steps, also while they are being retried; when a
    step fails, every step that depends on it is skipped (never run on stale inputs).
  * Priority (parallel mode): the longest notebooks first, using runtimes logged in html/runtimes.json by
    earlier runs, then the order in which steps were added.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

try:
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, DeadKernelError
except ImportError:  # pragma: no cover
    sys.exit("run_notebooks.py needs nbclient and nbformat (they are in environment.yml)")


def _now():
    return datetime.now().strftime("%H:%M:%S")


def _uses_stata(nb):
    src = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
    return "import stata_init" in src or "%%stata" in src or "stata_setup.config" in src


def _kernel(nb):
    ks = nb.metadata.get("kernelspec", {})
    lang = (ks.get("language") or nb.metadata.get("language_info", {}).get("name", "")).lower()
    return "ir" if lang == "r" or ks.get("name") == "ir" else "python3"


def stata_licence(stata_location=None, version="mp"):
    """(seats, cores) from the Stata start-up banner, e.g. '4-user 8-core network' -> (4, 8); None if unknown."""
    cands = []
    if stata_location:
        cands += [Path(stata_location) / f"stata-{version}", Path(stata_location) / "stata",
                  Path(stata_location) / f"Stata{version.upper()}.app/Contents/MacOS/stata-{version}"]
    cands += [Path(p) for p in (os.popen("command -v stata-mp stata-se stata 2>/dev/null").read().split())]
    for exe in cands:
        if exe.exists():
            try:
                out = subprocess.run([str(exe)], input="exit, clear\n", capture_output=True, text=True, timeout=60).stdout
            except Exception:
                continue
            m = re.search(r"(\d+)-user(?:\s+(\d+)-core)?", out)
            if m:
                return int(m.group(1)), int(m.group(2) or 1)
            m = re.search(r"Single-user(?:\s+(\d+)-core)?", out, re.I)
            if m:
                return 1, int(m.group(1) or 1)
    return None


class Step:
    def __init__(self, path, name, after, uses, kernel, start_cells):
        self.path, self.name, self.after, self.uses = Path(path), name, list(after), dict(uses)
        self.kernel, self.start_cells = kernel, start_cells
        self.status, self.attempts, self.seconds, self.error, self.order = "pending", 0, None, "", 0


class Runner:
    def __init__(self, parallel=False, max_parallel=None, limits=None, html_dir="html", runtimes="html/runtimes.json",
                 retry_every=300, retry_for=24 * 3600, stata_location=None, stata_version="mp", show=True, export_html=True):
        self.parallel = parallel
        self.max_parallel = max_parallel or max(1, (os.cpu_count() or 2) // 2)
        self.limits = dict(limits or {})
        self.html_dir, self.runtimes_file = Path(html_dir), Path(runtimes)
        self.retry_every, self.retry_for = retry_every, retry_for
        self.stata_location, self.stata_version = stata_location, stata_version
        self.show, self.export_html = show, export_html
        self.steps, self._lock, self._cv = {}, threading.Lock(), threading.Condition()
        self.runtimes = {}
        try:
            self.runtimes = json.loads(self.runtimes_file.read_text())
        except (OSError, ValueError):
            pass

    # ------------------------------------------------------------------ registering / running
    def step(self, path, after=(), uses=None, name=None, kernel=None, start_cells=1):
        """Add a notebook. Sequential mode: run it now. Parallel mode: run it in run_all()."""
        path = Path(path)
        nb = nbformat.read(path, as_version=4)
        name = name or path.stem
        u = dict(uses or {})
        if _uses_stata(nb):
            u.setdefault("stata", 1)
        s = Step(path, name, after, u, kernel or _kernel(nb), start_cells)
        s.order = len(self.steps)
        self.steps[name] = s
        if not self.parallel:
            missing = [d for d in s.after if self.steps.get(d) is None or self.steps[d].status != "ok"]
            if missing:
                s.status, s.error = "skipped", f"waits for {', '.join(missing)} (not run or failed)"
                print(f"[{_now()}] ⏭  {name}: skipped — {s.error}")
            else:
                self._execute(s)
            self._show(s)
        return s

    def run_all(self):
        """Parallel mode: run every pending step respecting limits, dependencies and priority. Prints a summary."""
        if self.parallel:
            self._schedule()
        return self.summary()

    # ------------------------------------------------------------------ scheduler
    def _limit(self, res):
        if res in self.limits:
            return self.limits[res]
        if res == "stata":
            lic = stata_licence(self.stata_location, self.stata_version)
            cores = os.cpu_count() or 2
            if lic:
                seats, per = lic
                self.limits["stata"] = max(1, min(seats, cores // max(per, 1) or 1))
                print(f"[{_now()}] Stata licence: {seats} seat(s), {per} core(s) per session → at most "
                      f"{self.limits['stata']} Stata notebook(s) at once")
            else:
                self.limits["stata"] = 1
                print(f"[{_now()}] Stata licence not read from the banner → 1 Stata notebook at a time "
                      f"(set Runner(limits={{'stata': N}}) to change)")
            return self.limits["stata"]
        return self.max_parallel

    def _priority(self, s):
        return (-float(self.runtimes.get(s.name, 0)), s.order)

    def _schedule(self):
        in_use, running = {}, 0
        pending = [s for s in self.steps.values() if s.status == "pending"]
        for s in pending:
            unknown = [d for d in s.after if d not in self.steps]
            if unknown:
                s.status, s.error = "skipped", f"unknown dependency {', '.join(unknown)}"
        threads = []

        def worker(s):
            nonlocal running
            try:
                self._execute(s)
            finally:
                with self._cv:
                    running -= 1
                    for r, n in s.uses.items():
                        in_use[r] -= n
                    self._cv.notify_all()

        with self._cv:
            while True:
                waiting = sorted((s for s in self.steps.values() if s.status == "pending"), key=self._priority)
                # skip dependents of failed/skipped steps
                changed = True
                while changed:
                    changed = False
                    for s in waiting:
                        bad = [d for d in s.after if self.steps[d].status in ("failed", "skipped")]
                        if bad and s.status == "pending":
                            s.status, s.error = "skipped", f"input step {', '.join(bad)} did not succeed"
                            print(f"[{_now()}] ⏭  {s.name}: skipped — {s.error}")
                            changed = True
                    waiting = [s for s in waiting if s.status == "pending"]
                if not waiting and running == 0:
                    break
                started = False
                for s in waiting:
                    if running >= self.max_parallel:
                        break
                    if any(self.steps[d].status != "ok" for d in s.after):
                        continue
                    if any(in_use.get(r, 0) + n > self._limit(r) for r, n in s.uses.items()):
                        continue
                    for r, n in s.uses.items():
                        in_use[r] = in_use.get(r, 0) + n
                    running += 1
                    s.status = "running"
                    t = threading.Thread(target=worker, args=(s,), daemon=True)
                    threads.append(t)
                    t.start()
                    started = True
                if not started:
                    self._cv.wait(timeout=5)
        for t in threads:
            t.join()

    # ------------------------------------------------------------------ one notebook
    def _execute(self, s):
        s.status = "running"
        t0, deadline = time.time(), time.time() + self.retry_for
        while True:
            s.attempts += 1
            print(f"[{_now()}] ▶  {s.name} (attempt {s.attempts}, kernel {s.kernel}"
                  + (f", uses {s.uses}" if s.uses else "") + ")", flush=True)
            nb = nbformat.read(s.path, as_version=4)
            client = NotebookClient(nb, timeout=None, kernel_name=s.kernel, allow_errors=False,
                                    resources={"metadata": {"path": str(s.path.parent.resolve())}})
            outcome, err = "ok", ""
            try:
                client.execute()
            except (CellExecutionError, DeadKernelError, RuntimeError, TimeoutError, OSError) as e:
                err = str(e)
                outcome = "start" if self._failed_at_start(nb, e, s.start_cells) else "failed"
            except Exception as e:  # anything else is a real failure
                err, outcome = "".join(traceback.format_exception_only(type(e), e)), "failed"
            finally:
                self._save(s, nb)
            if outcome == "start" and time.time() + self.retry_every < deadline:
                print(f"[{_now()}] ⏸  {s.name} could not start ({err.strip().splitlines()[-1][:120] if err.strip() else 'kernel'}); "
                      f"retrying in {self.retry_every}s", flush=True)
                time.sleep(self.retry_every)
                continue
            s.seconds = round(time.time() - t0, 1)
            s.status = "ok" if outcome == "ok" else "failed"
            s.error = "" if outcome == "ok" else (err.strip().splitlines() or ["failed"])[-1][:300]
            print(f"[{_now()}] {'✅' if s.status == 'ok' else '❌'} {s.name} {s.status} in {s.seconds:.0f}s"
                  + (f": {s.error}" if s.error else ""), flush=True)
            if s.status == "ok":
                with self._lock:
                    self.runtimes[s.name] = s.seconds
                    try:
                        self.runtimes_file.parent.mkdir(parents=True, exist_ok=True)
                        self.runtimes_file.write_text(json.dumps(self.runtimes, indent=1, sort_keys=True))
                    except OSError:
                        pass
            return s

    @staticmethod
    def _failed_at_start(nb, exc, start_cells):
        if isinstance(exc, DeadKernelError) or "Kernel died" in str(exc) or "kernel" in type(exc).__name__.lower():
            executed = [c for c in nb.cells if c.cell_type == "code" and c.get("execution_count")]
            return len(executed) <= start_cells
        code = [c for c in nb.cells if c.cell_type == "code" and c.source.strip()]
        for i, c in enumerate(code):
            if any(o.get("output_type") == "error" for o in c.get("outputs", [])):
                return i < start_cells
        # no cell reported an error: the kernel never ran a cell (start-up failure) or died later
        return not any(c.get("execution_count") for c in code)

    def _save(self, s, nb):
        ks = nb.metadata.setdefault("kernelspec", {"name": s.kernel, "language": "R" if s.kernel == "ir" else "python"})
        ks.setdefault("display_name", "R" if s.kernel == "ir" else "Python 3")   # required for a valid notebook / HTML
        try:
            nbformat.write(nb, s.path)
        except Exception as e:  # never lose the run because saving failed
            print(f"[{_now()}] ⚠️  could not save {s.path}: {e}")
        if self.export_html:
            try:
                from nbconvert import HTMLExporter
                body, _ = HTMLExporter().from_notebook_node(nb)
                self.html_dir.mkdir(parents=True, exist_ok=True)
                (self.html_dir / f"{s.name}.html").write_text(body, encoding="utf-8")
            except Exception as e:
                print(f"[{_now()}] ⚠️  could not export {s.name}.html: {e}")

    # ------------------------------------------------------------------ display
    def _show(self, s):
        if not self.show:
            return
        try:
            from IPython import get_ipython
            from IPython.display import IFrame, display
            if get_ipython() is not None and (self.html_dir / f"{s.name}.html").exists():
                display(IFrame(str(self.html_dir / f"{s.name}.html"), width=800, height=400))
        except ImportError:
            pass

    def summary(self):
        icon = {"ok": "✅", "failed": "❌", "skipped": "⏭", "pending": "…", "running": "▶"}
        rows = [f"| {icon[s.status]} | {s.name} | {s.status} | {s.attempts} | {s.seconds or ''} | {s.error} |"
                for s in sorted(self.steps.values(), key=lambda x: x.order)]
        text = "| | Step | Status | Attempts | Seconds | Note |\n|---|---|---|---|---|---|\n" + "\n".join(rows)
        try:
            from IPython import get_ipython
            from IPython.display import Markdown, display
            if get_ipython() is not None and self.show:
                display(Markdown(text))
            else:
                print(text)
        except ImportError:
            print(text)
        return {s.name: s.status for s in self.steps.values()}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebooks", nargs="+", help="path[:after=A,B][:uses=res=n]")
    ap.add_argument("--parallel", type=int, default=0, help="run in parallel with this many notebooks at once")
    ap.add_argument("--limit", action="append", default=[], help="resource=N, e.g. stata=2")
    ap.add_argument("--retry-every", type=float, default=300)
    ap.add_argument("--retry-for", type=float, default=24 * 3600)
    ap.add_argument("--stata-location", default=None)
    ap.add_argument("--stata-version", default="mp")
    a = ap.parse_args(argv)
    r = Runner(parallel=a.parallel > 0, max_parallel=a.parallel or 1, limits={k: int(v) for k, v in (x.split("=") for x in a.limit)},
               retry_every=a.retry_every, retry_for=a.retry_for, stata_location=a.stata_location,
               stata_version=a.stata_version, show=False)
    for spec in a.notebooks:
        parts = spec.split(":")
        kw = {"after": [], "uses": {}}
        for p in parts[1:]:
            k, v = p.split("=", 1)
            if k == "after":
                kw["after"] = [x for x in v.split(",") if x]
            elif k == "uses":
                rn, n = v.split("=") if "=" in v else (v, 1)
                kw["uses"][rn] = int(n)
        r.step(parts[0], **kw)
    status = r.run_all()
    sys.exit(0 if all(v == "ok" for v in status.values()) else 1)


if __name__ == "__main__":
    main()
