"""HTTP API against a temp repo copy, with the real engine worker and a fake latex worker."""

from __future__ import annotations

import json
import time

from click.testing import CliRunner

from .conftest import git, wait_job

SEMINAR = "sheets/sem2/seminar-demo.yaml"
SEM1 = "sheets/sem1/kontrolnaya.yaml"


def test_engine_and_health(client):
    assert client.get("/api/health").json() == {"ok": True}
    assert client.get("/api/tasks").status_code == 200  # waits for the warm-up
    e = client.get("/api/engine").json()
    assert e["tasks"] >= 30 and e["import_errors"] == {}


def test_list_and_get_task(client):
    r = client.get("/api/tasks").json()
    ids = {t["id"] for t in r["tasks"]}
    assert "dlp.shanks" in ids and r["import_errors"] == {}
    r = client.get("/api/tasks", params={"topic": "dlp", "complexity": "1"}).json()
    assert r["tasks"] and all(t["complexity"] == 1 and t["id"].startswith("dlp.")
                              for t in r["tasks"])
    t = client.get("/api/tasks/dlp.shanks").json()
    assert t["file"] == "taskgen/tasks/dlp/dlp_mod_p.py"
    assert t["meta"]["fields"]["complexity"]["value"] == 1
    assert t["info"]["preset_values"]["default"]["primes"]
    assert "class Shanks(Task)" in t["source"]
    assert client.get("/api/tasks/nope.nope").status_code == 404


def test_preview_and_validate(client):
    r = client.post("/api/tasks/dlp.shanks/preview", json={"seed": 3, "count": 2}).json()
    assert r["seed"] == 3 and len(r["instances"]) == 2 and r["pdf"] is None
    again = client.post("/api/tasks/dlp.shanks/preview", json={"seed": 3, "count": 2}).json()
    assert again["instances"] == r["instances"]
    # unsaved template override
    r = client.post("/api/tasks/dlp.shanks/preview",
                    json={"seed": 3, "count": 1, "statement": r"Решить $\VAR{g}^x = \VAR{h}$."}).json()
    assert r["instances"][0]["statement"].startswith("Решить $")
    # PDF via the latex worker
    r = client.post("/api/tasks/dlp.shanks@default/preview", json={"seed": 1, "pdf": True}).json()
    assert r["pdf"] == "build/web/preview/dlp.shanks_default.pdf"
    assert client.get(f"/api/files/{r['pdf']}").status_code == 200
    # errors map to HTTP codes
    assert client.post("/api/tasks/dlp.shanks@sem9/preview", json={}).status_code == 400
    assert client.post("/api/tasks/no.such/preview", json={}).status_code == 404
    v = client.post("/api/tasks/crypto.lcg/validate", json={"count": 3}).json()
    assert v["ok"] and len(v["results"]) == 2
    listed = {t["id"]: t for t in client.get("/api/tasks").json()["tasks"]}
    assert listed["crypto.lcg"]["validation"]["ok"] is True


def test_validate_all_job_streams_progress(client):
    job = client.post("/api/validate", json={"count": 1}).json()["job"]
    with client.stream("GET", f"/api/jobs/{job}/events") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert events[0]["status"] == "queued" and events[-1]["status"] == "done"
    logs = [e for e in events if e["type"] == "log"]
    assert logs and logs[-1]["done"] == logs[-1]["total"]
    assert events[-1]["result"]["ok"]


def test_sheets_list_get(client):
    sheets = {s["path"]: s for s in client.get("/api/sheets").json()}
    assert sheets[SEM1]["kind"] == "individual" and sheets[SEM1]["variants"] == 126
    assert sheets[SEMINAR]["kind"] == "classroom"
    assert client.get("/api/sheets/sheets/sem2/nope.yaml").status_code == 404
    assert client.get("/api/sheets/taskgen/tasks/taxonomy.yaml").status_code == 400
    s = client.get(f"/api/sheets/{SEMINAR}").json()
    assert s["problems"] == [] and s["data"]["id"] == "sem2-seminar-demo"
    assert client.get("/api/sheets/sheets/../taskgen/x.yaml").status_code in (400, 404)
    schema = client.get("/api/schema/sheet").json()
    assert "IndividualSheet" in schema["$defs"]


def test_sheet_save_validates_first(client, clean_repo):
    path = clean_repo / SEMINAR
    before = path.read_text(encoding="utf-8")
    bad = before.replace("dlp.shanks", "dlp.nope")
    r = client.put(f"/api/sheets/{SEMINAR}", json={"raw": bad})
    assert r.status_code == 422 and "unknown task id" in r.json()["problems"][0]
    assert path.read_text(encoding="utf-8") == before  # invalid YAML is never written
    good = before.replace("title: Решётки", "title: Решётки и CVP")
    assert client.put(f"/api/sheets/{SEMINAR}", json={"raw": good}).status_code == 200
    assert path.read_text(encoding="utf-8") == good


def test_sheet_merge_validate_stats_create(client, clean_repo):
    raw = (clean_repo / SEM1).read_text(encoding="utf-8")
    data = client.post("/api/sheets/validate", json={"yaml": raw}).json()
    assert data["problems"] == []
    d = data["data"]
    d["groups"][0]["count"] = 3
    merged = client.post("/api/sheets/merge", json={"base": raw, "data": d}).json()["raw"]
    assert merged.splitlines()[0] == raw.splitlines()[0]  # comment kept
    assert "count: 3" in merged
    st = client.post("/api/sheets/stats", json={"yaml": merged, "seed": 1}).json()
    assert st["variants"] == 87
    assert client.post("/api/sheets/validate", json={"yaml": "id: [\n"}).json()["problems"]
    r = client.post("/api/sheets", json={"path": "sheets/sem1/new.yaml", "kind": "classroom",
                                         "id": "sem1-new", "title": "Новый"})
    assert r.status_code == 201 and (clean_repo / "sheets/sem1/new.yaml").is_file()
    assert client.post("/api/sheets", json={"path": "sheets/sem1/new2.yaml", "kind": "classroom",
                                            "id": "sem1-new", "title": "x"}).status_code == 409


def test_draft_job_builds_every_group_pdf(client):
    client.fake_latex.built.clear()
    job = client.post("/api/runs/draft", json={"path": SEM1, "seed": 5}).json()["job"]
    j = wait_job(client, job)
    assert j["status"] == "done", j["error"]
    res = j["result"]
    assert res["out_dir"] == "build/sheets/sem1-kontrolnaya" and res["draft"]
    assert res["files"] == [f"{s}-{g}.tex" for g in ("6411", "6412", "6413")
                            for s in ("tasks", "tasks_solutions")]
    assert len(res["pdfs"]) == 6 and len(client.fake_latex.built) == 6
    # unsaved yaml + variant subset
    raw = (client.ctx.repo / SEMINAR).read_text(encoding="utf-8")
    j = wait_job(client, client.post("/api/runs/draft", json={"yaml": raw, "seed": 1}).json()["job"])
    assert j["result"]["files"] == ["tasks.tex", "tasks_solutions.tex"]


def test_draft_job_reports_latex_failure(client):
    client.fake_latex.fail = {"tasks_solutions.tex"}
    try:
        j = wait_job(client, client.post("/api/runs/draft", json={"path": SEMINAR}).json()["job"])
    finally:
        client.fake_latex.fail = set()
    assert j["status"] == "failed" and "LaTeX build failed" in j["error"]["message"]


def test_issue_on_dirty_tree_warns_and_records_it(client, clean_repo):
    (clean_repo / "sheets" / "scratch.txt").write_text("x")
    r = client.post("/api/runs/issue", json={"path": SEMINAR, "seed": 1})
    assert r.status_code == 200, r.text  # a warning, not a block
    j = wait_job(client, r.json()["job"])
    assert j["status"] == "done", j["error"]
    assert "sheets/scratch.txt" in j["result"]["dirty_files"]
    assert any(e.get("level") == "warning" and e.get("step") == "git" for e in j["events"])
    m = json.loads((clean_repo / j["result"]["manifest"]).read_text(encoding="utf-8"))
    assert m["git"]["dirty"] is True
    assert set(j["result"]["sealed"]) == {"tasks.pdf", "tasks_solutions.pdf"}
    assert {"tasks.pdf", "tasks_solutions.pdf"} <= set(m["files"])


def test_issue_matches_cli_and_regen(client, repo, monkeypatch):
    """Invariant: web-issued and CLI-issued runs (same sheet + seed) have
    byte-identical .tex and identical manifest variants."""
    r = client.post("/api/runs/issue", json={"path": SEM1, "seed": 77})
    assert r.status_code == 200, r.text  # clean tree
    j = wait_job(client, r.json()["job"])
    assert j["status"] == "done", j["error"]
    web_dir = repo / j["result"]["out_dir"]

    # the CLI, in-process, against the same temp repo
    import os

    import taskgen.core.audit as audit
    from taskgen.cli import main
    monkeypatch.chdir(repo)
    monkeypatch.setattr(audit, "ARCHIVE_DIR", repo / "build" / "cli-archive")
    monkeypatch.setattr(audit, "REPO_ROOT", repo)
    out = CliRunner().invoke(main, ["gen", SEM1, "--seed", "77", "--quiet"])
    assert out.exit_code == 0, out.output
    cli_dir = repo / out.output.strip().splitlines()[-1]
    assert os.path.isdir(cli_dir)
    a = json.loads((web_dir / "manifest.json").read_text(encoding="utf-8"))
    b = json.loads((cli_dir / "manifest.json").read_text(encoding="utf-8"))
    assert a["variants"] == b["variants"] and a["spec_path"] == b["spec_path"] == SEM1
    for name in b["files"]:
        assert (web_dir / name).read_bytes() == (cli_dir / name).read_bytes(), name

    # archive browser + verification
    arch = client.get("/api/archive").json()
    run = next(r for s in arch if s["sheet_id"] == "sem1-kontrolnaya" for r in s["runs"])
    assert run["master_seed"] == 77 and len(run["sealed"]) == 6
    d = client.get(f"/api/archive/sem1-kontrolnaya/{run['run']}").json()
    assert d["manifest"]["layout"] == "per-group" and "manifest.json" in d["files_on_disk"]
    j = wait_job(client, client.post(f"/api/archive/sem1-kontrolnaya/{run['run']}/regen",
                                     json={}).json()["job"])
    assert j["result"]["identical"], j
    j = wait_job(client, client.post(f"/api/archive/sem1-kontrolnaya/{run['run']}/regen",
                                     json={"variants": ["6412/3"]}).json()["job"])
    assert j["result"]["identical"] and j["result"]["checked"] == ["6412/3"]
    assert client.get("/api/archive/sem1-kontrolnaya/../x").status_code in (400, 404)
    git(repo, "clean", "-qfd", "archive")


def test_files_whitelist(client):
    assert client.get("/api/files/taskgen/core/audit.py").status_code in (400, 404)
    assert client.get("/api/files/build/../taskgen/__init__.py").status_code in (400, 404)
    assert client.get("/api/files/build/nope.pdf").status_code == 404


def test_git_status_and_diff(client, clean_repo):
    s = client.get("/api/git/status").json()
    assert s["available"] and s["dirty"] is False
    p = clean_repo / "sheets/sem2/seminar-demo.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "# edit\n", encoding="utf-8")
    s = client.get("/api/git/status").json()
    assert s["dirty"] and s["dirty_files"] == ["sheets/sem2/seminar-demo.yaml"]
    d = client.get("/api/git/diff", params={"path": "sheets/sem2/seminar-demo.yaml"}).text
    assert "+# edit" in d
    head = client.get("/api/git/head", params={"path": "sheets/sem2/seminar-demo.yaml"}).json()
    assert "# edit" not in head["content"]


def test_task_meta_edit_restarts_worker(client, clean_repo):
    restarts = client.ctx.worker.restarts
    r = client.patch("/api/tasks/dlp.shanks/meta", json={"values": {"title_ru": "Шенкс!", "complexity": 2}})
    assert r.status_code == 200, r.text
    assert 'title_ru = r"Шенкс!"' in (clean_repo / "taskgen/tasks/dlp/dlp_mod_p.py").read_text()
    t = {x["id"]: x for x in client.get("/api/tasks").json()["tasks"]}["dlp.shanks"]
    assert t["title"] == "Шенкс!" and t["complexity"] == 2  # fresh worker, no stale module
    assert client.ctx.worker.restarts > restarts
    r = client.patch("/api/tasks/dlp.shanks/meta", json={"values": {"statement": "x"}})
    assert r.status_code == 400


def test_broken_module_does_not_hide_other_tasks(client, clean_repo):
    f = clean_repo / "taskgen/tasks/ecc/scalar_mult.py"
    src = f.read_text(encoding="utf-8")
    r = client.put("/api/modules", json={"path": "taskgen/tasks/ecc/scalar_mult.py",
                                         "source": src + "\nraise RuntimeError('wip')\n"})
    assert r.json()["ok"]  # saved as-is (valid syntax, fails at import)
    listed = client.get("/api/tasks").json()
    assert "taskgen.tasks.ecc.scalar_mult" in listed["import_errors"]
    tasks = {t["id"]: t for t in listed["tasks"]}
    assert tasks["dlp.shanks"]["broken"] is False
    assert tasks["ecc.double_and_add_binary"]["broken"] is True
    t = client.get("/api/tasks/ecc.double_and_add_binary").json()
    assert "wip" in t["import_error"] and t["info"] is None
    # a syntax error is written too (work in progress is never lost)
    r = client.put("/api/tasks/ecc.double_and_add_binary/source", json={"source": src + "\ndef (:\n"})
    assert r.json()["ok"] is False and r.json()["syntax_error"]
    assert f.read_text(encoding="utf-8").endswith("def (:\n")
    assert client.get("/api/tasks/ecc.double_and_add_binary").status_code == 200


def test_scaffold_task(client, clean_repo):
    body = {"task_id": "dlp.toy", "class_name": "Toy", "title": "Игрушечная задача",
            "topic": "dlp.generic", "module": "dlp/toy.py"}
    r = client.post("/api/tasks", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["file"] == "taskgen/tasks/dlp/toy.py"
    p = client.post("/api/tasks/dlp.toy/preview", json={"seed": 1}).json()
    assert p["instances"][0]["task_id"] == "dlp.toy"
    assert client.post("/api/tasks", json=body).status_code == 409
    r = client.post("/api/tasks", json={**body, "task_id": "x.y", "module": "new_topic/sub/m.py"})
    assert r.status_code == 201
    assert (clean_repo / "taskgen/tasks/new_topic/__init__.py").is_file()
    assert (clean_repo / "taskgen/tasks/new_topic/sub/__init__.py").is_file()


def test_topics_edit(client, clean_repo):
    topics = client.get("/api/topics").json()
    items = [{"slug": t["slug"], "title": t["title"]} for t in topics]
    # removing a topic in use is refused
    r = client.put("/api/topics", json={"items": [i for i in items if i["slug"] != "dlp.generic"]})
    assert r.status_code == 422 and "dlp.shanks" in json.dumps(r.json())
    r = client.put("/api/topics", json={"items": items + [{"slug": "x.y", "title": "X"}]})
    assert r.status_code == 422 and "parent 'x' missing" in json.dumps(r.json())
    r = client.put("/api/topics", json={"items": items + [{"slug": "misc", "title": "Разное"}]})
    assert r.status_code == 200 and any(t["slug"] == "misc" for t in r.json())
    text = (clean_repo / "taskgen/tasks/taxonomy.yaml").read_text(encoding="utf-8")
    assert text.startswith("# Topic taxonomy") and "misc: Разное" in text


def test_latex_macros(client):
    m = client.get("/api/latex/macros").json()
    assert m["ZZ"] == r"\mathbb{Z}" and m["Zn"] == [r"\ZZ/#1\ZZ", 1]
    assert m["ord"] == r"\operatorname{ord}"


def test_spa_fallback(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    r = client.get("/tasks/dlp.shanks")
    assert r.status_code in (200, 404)  # 404 only when the SPA is not built


def test_engine_timeout_restarts_worker(client):
    from taskgen_web.worker import EngineTimeout

    w = client.ctx.worker
    client.get("/api/tasks")  # respawn now if a previous test left the worker stale
    before = w.restarts

    async def slow():
        return await w.call("validate", target="all", count=10_000, timeout=1)

    t0 = time.time()
    try:
        client.portal.call(slow)  # type: ignore[attr-defined]
    except EngineTimeout:
        pass
    else:
        raise AssertionError("expected a timeout")
    assert time.time() - t0 < 30 and w.restarts == before + 1
    assert client.get("/api/tasks/dlp.shanks").status_code == 200  # respawned on demand
