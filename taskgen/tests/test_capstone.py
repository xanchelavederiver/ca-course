"""Capstone pipeline (taskgen.capstone) on a toy capstone: vectors, runner, report."""

import json
import sys
import textwrap

import pytest

from taskgen.capstone import config, report, runner, vectors

SOLVER = textwrap.dedent("""
    import json, sys, time
    mode = sys.argv[1]
    for line in sys.stdin:
        req = json.loads(line)
        n = req["input"]["n"]
        if mode == "slow" and req["id"].endswith("001"):
            time.sleep(30)
        if mode == "crash" and req["id"].endswith("002"):
            sys.exit(3)
        p = next(d for d in range(2, n) if n % d == 0)
        if mode == "wrong":
            p += 1
        print(json.dumps({"id": req["id"], "output": {"p": p}, "extra": {"trial": True}}), flush=True)
""")


@pytest.fixture
def root(tmp_path):
    (tmp_path / "capstone.yaml").write_text(
        "slack: 10\ntimeout: 20\ncapstones:\n  - {n: 1, slug: toy, title: Toy}\n", encoding="utf-8")
    d = tmp_path / "01-toy"
    (d / "bench").mkdir(parents=True)
    (d / "solver.py").write_text(SOLVER, encoding="utf-8")
    (d / "bench" / "config.yaml").write_text(textwrap.dedent(f"""
        generator: taskgen.tests.capstone_toy
        seed: 7
        command: {sys.executable} solver.py ok
        x_label: k
        sizes:
          - {{name: small, x: 10, count: 4, params: {{k: 10}}}}
          - {{name: big, x: 60, count: 4, commit: false, timeout: 2, params: {{k: 60}}}}
        requirements:
          ReqK: {{value: 60}}
          ReqSeconds: {{size: big, stat: max, unit: ms}}
          ReqRaw: {{size: big, stat: median, slack: false, round: none}}
    """), encoding="utf-8")
    return tmp_path


def test_vectors_deterministic_and_checked(root):
    cap = config.load("toy", root)
    assert vectors.write(cap, log=lambda *_: None)
    first = (cap.vectors_dir / "small.jsonl").read_text()
    man = json.loads((cap.vectors_dir / "manifest.json").read_text())
    assert man["seed"] == 7 and set(man["sizes"]) == {"small", "big"}
    assert (cap.vectors_dir / ".gitignore").read_text().endswith("/big.jsonl\n")
    assert vectors.write(cap, check=True, log=lambda *_: None)
    assert vectors.write(cap, force=True, log=lambda *_: None)
    assert (cap.vectors_dir / "small.jsonl").read_text() == first
    v = vectors.load(cap, "small")
    assert [x["id"] for x in v] == ["small-000", "small-001", "small-002", "small-003"]
    (cap.vectors_dir / "small.jsonl").write_text(first.replace('"n":', '"n": ', 1))
    assert not vectors.write(cap, check=True, log=lambda *_: None)


def _run(root, mode):
    cap = config.load("toy", root)
    vectors.write(cap, log=lambda *_: None)
    cmd = f"{sys.executable} solver.py {mode}"
    return cap, runner.run(cap, cmd, cap.dir, log=lambda *_: None)


def test_run_ok_wrong(root):
    cap, recs = _run(root, "ok")
    assert [r.status for r in recs] == ["ok"] * 8
    assert all(r.wall_s is not None and r.wall_s < 2 for r in recs)
    assert recs[0].extra == {"trial": True}
    _, recs = _run(root, "wrong")
    assert {r.status for r in recs} == {"wrong"}


def test_run_timeout_and_crash_recover(root):
    cap = config.load("toy", root)
    vectors.write(cap, log=lambda *_: None)
    recs = runner.run(cap, f"{sys.executable} solver.py slow", cap.dir, sizes=["big"],
                      log=lambda *_: None)
    assert [r.status for r in recs] == ["ok", "timeout", "ok", "ok"]
    recs = runner.run(cap, f"{sys.executable} solver.py crash", cap.dir, sizes=["small"],
                      log=lambda *_: None)
    assert [r.status for r in recs] == ["ok", "ok", "crash", "ok"]
    assert "code 3" in recs[2].message


def test_bench_report_requirements(root):
    cap = config.load("toy", root)
    vectors.write(cap, log=lambda *_: None)
    raw = runner.bench(cap, out=root / "raw.json", log=lambda *_: None)
    warnings = report.report(cap, raw, log=lambda *_: None)
    assert warnings == []
    res = json.loads((cap.bench_dir / "results.json").read_text())
    assert res["slack"] == 10 and res["summary"]["big"]["ok"] == 4
    assert res["machine"]["cpu_count"] >= 1
    tex = (cap.dir / "requirements.tex").read_text()
    assert "\\newcommand{\\ReqK}{60}" in tex and "\\newcommand{\\ReqSlack}{10}" in tex
    secs = res["requirements"]["ReqSeconds"]
    assert float(secs.replace("{,}", ".")) >= 10 * res["summary"]["big"]["max_s"] * 1000 * 0.999
    assert (cap.bench_dir / "plot.png").exists() and (cap.bench_dir / "results.md").exists()
    assert runner.check(cap, f"{sys.executable} solver.py ok", cap.dir, log=lambda *_: None)
    assert not runner.check(cap, f"{sys.executable} solver.py wrong", cap.dir, log=lambda *_: None)
    cap20 = config.load("toy", root, slack=20)
    assert report.requirements(cap20, report.summarize(cap20, json.loads(raw.read_text())))[0][
        "ReqSlack"] == "20"


@pytest.mark.parametrize("x,want", [(0.7, 1), (1, 1), (1.01, 2), (3, 5), (5.5, 10), (42, 50),
                                    (0.0123, 0.02), (180, 200)])
def test_nice_up(x, want):
    assert report.nice_up(x) == pytest.approx(want)


def test_repo_capstones_load():
    for semester in (1, 2):
        root = config.semester_root(semester)
        for slug in config.slugs(root):
            cap = config.load(slug, root)
            assert cap.sizes and cap.command and cap.semester == semester
            gen = cap.gen()
            assert isinstance(gen.VERSION, int) and callable(gen.generate) and callable(gen.verify)


def test_semester_specific_raw_path(root):
    cap = config.load("toy", root, semester=1)
    assert config.raw_path(cap) == config.REPO / "build" / "capstone" / "sem1" / "toy" / "raw.json"


def test_per_op_stats(root):
    cap = config.load("toy", root)
    cap.requirements = {"ReqOpUs": {"size": "small", "stat": "median_op", "unit": "us"}}
    raw = {"sizes": ["small"], "records": [
        {"id": f"small-{i}", "size": "small", "tags": [], "status": "ok", "wall_s": 0.01 * (i + 1),
         "repeat": 1000, "rss_kb": 1} for i in range(3)]}
    s = report.summarize(cap, raw)["small"]
    assert s["median_op_s"] == pytest.approx(2e-5)
    assert report.requirements(cap, {"small": s})[0]["ReqOpUs"] == "200"
