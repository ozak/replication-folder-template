"""
Tests for the template's notebook runner (replication-package/progs/Python/run_notebooks.py) with
dummy notebooks: save on failure, resource limits, retry when a notebook cannot start, priority,
dependencies. Needs nbclient, nbformat, ipykernel, nbconvert.

    python3 -m unittest SKILL_DIR/tests/test_runner.py -v     # runner path: RUNNER env var or the bundled template
"""
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = Path(os.environ.get("RUNNER", HERE.parent / "assets/template/replication-package/progs/Python/run_notebooks.py"))
if not RUNNER.exists():  # inside the template repo
    RUNNER = HERE.parents[3] / "replication-package/progs/Python/run_notebooks.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_notebooks", RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def nb(path, cells):
    import nbformat
    n = nbformat.v4.new_notebook()
    n.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    n.cells = [nbformat.v4.new_code_cell(c) for c in cells]
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(n, path)
    return path


LOG = """import time, json, os, pathlib
def log(ev):
    with open({log!r}, "a") as fh:
        fh.write(json.dumps([{name!r}, ev, time.time()]) + "\\n")
"""


def worknb(root, name, seconds=0.6, stata=False, fail=False):
    cells = []
    if stata:
        cells.append("import stata_init")
    cells.append(LOG.format(log=str(root / "events.jsonl"), name=name) + "log('start')")
    cells.append(f"time.sleep({seconds})")
    if fail:
        cells.append("raise ValueError('boom')")
    cells.append("log('end')")
    return nb(root / "progs" / ("Stata" if stata else "Python") / f"{name}.ipynb", cells)


def events(root):
    p = root / "events.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def max_concurrent(evs, names=None):
    cur = best = 0
    for n, ev, _ in sorted(evs, key=lambda e: (e[2], e[1] == "start")):
        if names is not None and n not in names:
            continue
        cur += 1 if ev == "start" else -1
        best = max(best, cur)
    return best


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "progs/Stata").mkdir(parents=True)
        # a fake pystata start-up: fails while the file 'blocked' exists (= no free licence seat)
        (self.root / "progs/Stata/stata_init.py").write_text(
            f"import os\nif os.path.exists({str(self.root / 'blocked')!r}):\n    raise RuntimeError('no free Stata licence seat')\n")
        self.m = load_runner()
        self.cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def runner(self, **kw):
        kw.setdefault("show", False)
        kw.setdefault("retry_every", 0.5)
        return self.m.Runner(**kw)

    def test_save_on_failure_and_html(self):
        p = worknb(self.root, "Fails", fail=True)
        r = self.runner()
        s = r.step(p)
        self.assertEqual(s.status, "failed")
        import nbformat
        saved = nbformat.read(p, as_version=4)
        self.assertTrue(any(o.get("output_type") == "error" for c in saved.cells for o in c.get("outputs", [])))
        self.assertTrue((self.root / "html/Fails.html").exists())
        self.assertEqual(s.attempts, 1, "a failure after the first cell must not be retried")

    def test_sequential_dependency_skip(self):
        a = worknb(self.root, "A", fail=True)
        b = worknb(self.root, "B")
        r = self.runner()
        r.step(a)
        s = r.step(b, after=["A"])
        self.assertEqual(s.status, "skipped")
        self.assertEqual([e for e in events(self.root) if e[0] == "B"], [])

    def test_limits_total_and_stata(self):
        names = [f"S{i}" for i in range(4)]
        for n in names:
            worknb(self.root, n, seconds=1.0, stata=True)
        py = [f"P{i}" for i in range(3)]
        for n in py:
            worknb(self.root, n, seconds=1.0)
        r = self.runner(parallel=True, max_parallel=4, limits={"stata": 2})
        for n in names:
            r.step(f"progs/Stata/{n}.ipynb")
        for n in py:
            r.step(f"progs/Python/{n}.ipynb")
        st = r.run_all()
        self.assertTrue(all(v == "ok" for v in st.values()), st)
        ev = events(self.root)
        self.assertLessEqual(max_concurrent(ev), 4)
        self.assertLessEqual(max_concurrent(ev, set(names)), 2)
        self.assertGreaterEqual(max_concurrent(ev), 3, "Python notebooks must not count against the Stata limit")

    def test_retry_when_stata_cannot_start(self):
        (self.root / "blocked").write_text("x")
        worknb(self.root, "S", seconds=0.2, stata=True)
        threading.Timer(1.6, lambda: (self.root / "blocked").unlink()).start()
        r = self.runner()
        s = r.step("progs/Stata/S.ipynb")
        self.assertEqual(s.status, "ok")
        self.assertGreaterEqual(s.attempts, 2)

    def test_retry_gives_up(self):
        (self.root / "blocked").write_text("x")
        worknb(self.root, "S", seconds=0.1, stata=True)
        r = self.runner(retry_for=1.2)
        s = r.step("progs/Stata/S.ipynb")
        self.assertEqual(s.status, "failed")

    def test_priority_slow_first(self):
        for n in ("Quick", "Slow", "Medium"):
            worknb(self.root, n, seconds=0.3)
        Path("html").mkdir()
        Path("html/runtimes.json").write_text(json.dumps({"Slow": 3600, "Medium": 60, "Quick": 1}))
        r = self.runner(parallel=True, max_parallel=1)
        for n in ("Quick", "Slow", "Medium"):
            r.step(f"progs/Python/{n}.ipynb")
        r.run_all()
        starts = [e[0] for e in sorted(events(self.root), key=lambda e: e[2]) if e[1] == "start"]
        self.assertEqual(starts, ["Slow", "Medium", "Quick"])

    def test_dependencies_wait_through_retries_and_skip_after_failure(self):
        (self.root / "blocked").write_text("x")
        worknb(self.root, "Base", seconds=0.2, stata=True)       # retried until 'blocked' disappears
        worknb(self.root, "Uses-Base", seconds=0.1)
        worknb(self.root, "Broken", seconds=0.1, fail=True)
        worknb(self.root, "Uses-Broken", seconds=0.1)
        worknb(self.root, "Uses-Uses-Broken", seconds=0.1)
        threading.Timer(1.6, lambda: (self.root / "blocked").unlink()).start()
        r = self.runner(parallel=True, max_parallel=3)
        r.step("progs/Stata/Base.ipynb")
        r.step("progs/Python/Uses-Base.ipynb", after=["Base"])
        r.step("progs/Python/Broken.ipynb")
        r.step("progs/Python/Uses-Broken.ipynb", after=["Broken"])
        r.step("progs/Python/Uses-Uses-Broken.ipynb", after=["Uses-Broken"])
        st = r.run_all()
        self.assertEqual(st["Base"], "ok")
        self.assertEqual(st["Uses-Base"], "ok")
        self.assertEqual(st["Broken"], "failed")
        self.assertEqual(st["Uses-Broken"], "skipped")
        self.assertEqual(st["Uses-Uses-Broken"], "skipped")
        ev = {(e[0], e[1]): e[2] for e in events(self.root)}
        self.assertGreater(ev[("Uses-Base", "start")], ev[("Base", "end")])
        self.assertGreaterEqual(r.steps["Base"].attempts, 2)

    def test_runtimes_logged(self):
        worknb(self.root, "A", seconds=0.2)
        r = self.runner()
        r.step("progs/Python/A.ipynb")
        self.assertIn("A", json.loads(Path("html/runtimes.json").read_text()))

    def test_cli(self):
        worknb(self.root, "A", seconds=0.1)
        worknb(self.root, "B", seconds=0.1)
        with self.assertRaises(SystemExit) as e:
            self.m.main(["progs/Python/A.ipynb", "progs/Python/B.ipynb:after=A", "--parallel", "2"])
        self.assertEqual(e.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
