"""Run a solver over vector files: wall time, peak RSS, correctness per vector.

Standard library only (it also runs in the ``capstone-c`` image). One solver process
per size class (so peak RSS is per class); a request that exceeds its timeout kills the
process, the vector is recorded as ``timeout`` and a fresh process serves the rest.
With ``warmup`` the first vector of the first size class is solved once untimed in every
new process, so interpreter/library start-up (``import sage.all``) is not measured.
"""

from __future__ import annotations

import json
import os
import platform
import selectors
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from taskgen.capstone import vectors as vecs
from taskgen.capstone.config import Capstone


@dataclass
class Record:
    id: str
    size: str
    tags: list[str]
    status: str               # ok | wrong | error | timeout | crash
    wall_s: float | None
    rss_kb: int | None = None
    message: str = ""
    repeat: int = 1           # input["repeat"]: the solver repeats the operation (per-op timing)
    extra: dict | None = field(default=None, repr=False)


class SolverDied(Exception):
    pass


class Solver:
    """A long-running solver process speaking the JSON-lines contract."""

    def __init__(self, command: str, cwd: Path, env: dict | None = None):
        self.command, self.cwd = command, cwd
        # `exec` so that the pid (and its /proc status) is the solver, not the shell.
        self.proc = subprocess.Popen(
            ["sh", "-c", "exec " + command], cwd=cwd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, **(env or {})},
            bufsize=0)
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.proc.stdout, selectors.EVENT_READ, "out")
        self.sel.register(self.proc.stderr, selectors.EVENT_READ, "err")
        self.buf = b""
        self.stderr = b""

    def ask(self, req: dict, timeout: float) -> tuple[dict, float]:
        """Send one request; return (answer, wall seconds). Raises TimeoutError / SolverDied."""
        line = (json.dumps(req, separators=(",", ":")) + "\n").encode()
        t0 = time.perf_counter()
        try:
            self.proc.stdin.write(line)
            self.proc.stdin.flush()
        except BrokenPipeError as e:
            raise SolverDied(self._why()) from e
        deadline = t0 + timeout
        while b"\n" not in self.buf:
            left = deadline - time.perf_counter()
            if left <= 0:
                raise TimeoutError
            events = self.sel.select(left)
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 1 << 16)
                if key.data == "err":
                    self.stderr = (self.stderr + chunk)[-8192:]
                    if not chunk:
                        self.sel.unregister(key.fileobj)
                    continue
                if not chunk:
                    raise SolverDied(self._why())
                self.buf += chunk
        wall = time.perf_counter() - t0
        raw, self.buf = self.buf.split(b"\n", 1)
        try:
            return json.loads(raw), wall
        except json.JSONDecodeError as e:
            raise SolverDied(f"not a JSON line: {raw[:200]!r}") from e

    def rss_kb(self) -> int | None:
        """Peak resident set size so far (VmHWM), Linux only."""
        try:
            for ln in Path(f"/proc/{self.proc.pid}/status").read_text().splitlines():
                if ln.startswith("VmHWM:"):
                    return int(ln.split()[1])
        except OSError:
            pass
        return None

    def _why(self) -> str:
        try:
            self.proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        tail = self.stderr.decode(errors="replace").strip().splitlines()[-5:]
        return f"solver exited (code {self.proc.returncode}): " + " | ".join(tail)

    def close(self) -> None:
        if self.proc.poll() is None:
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
                self.proc.wait()
        self.sel.close()

    def kill(self) -> None:
        self.proc.kill()
        self.proc.wait()
        self.sel.close()


def run(cap: Capstone, command: str, cwd: Path, sizes: list[str] | None = None,
        limit: int | None = None, timeout: float | None = None, log=print,
        stop_after_timeouts: int = 2) -> list[Record]:
    """Run ``command`` over the size classes. ``limit`` = vectors per class (default all).

    After ``stop_after_timeouts`` timeouts in a class, the rest of that class (and all
    larger classes) are recorded as ``timeout`` without running, so a slow solver does
    not take hours.
    """
    gen = cap.gen()
    classes = [s for s in cap.sizes if not sizes or s.name in sizes]
    warm = None
    if cap.warmup and cap.sizes:
        first = vecs.load(cap, cap.sizes[0].name)
        warm = {"id": "__warmup__", "input": first[0]["input"]} if first else None
    records: list[Record] = []
    give_up = False
    for size in classes:
        vs = vecs.load(cap, size.name)[:limit]
        t_out = float(timeout or cap.timeout_for(size))
        solver = None
        n_timeouts = 0
        for v in vs:
            if give_up:
                records.append(Record(v["id"], size.name, v["tags"], "timeout", None,
                                      message="skipped: smaller class timed out"))
                continue
            if solver is None:
                solver = Solver(command, cwd)
                if warm:
                    try:
                        solver.ask(warm, t_out)
                    except (TimeoutError, SolverDied) as e:
                        log(f"  warm-up failed: {e or 'timeout'}")
            rec = _one(solver, v, gen, t_out)
            if rec.status in ("timeout", "crash"):
                solver.kill()
                solver = None
                n_timeouts += rec.status == "timeout"
            records.append(rec)
            log(f"  {rec.id:<14} {rec.status:<7} "
                f"{'' if rec.wall_s is None else f'{rec.wall_s:10.4f}s'}"
                f"{'' if not rec.message else '  ' + rec.message[:120]}")
            if n_timeouts >= stop_after_timeouts:
                give_up = True
        if solver is not None:
            solver.close()
    return records


def _one(solver: Solver, v: dict, gen, t_out: float) -> Record:
    rec = _ask(solver, v, gen, t_out)
    inp = v.get("input")
    rec.repeat = int(inp.get("repeat", 1)) if isinstance(inp, dict) else 1
    return rec


def _ask(solver: Solver, v: dict, gen, t_out: float) -> Record:
    try:
        ans, wall = solver.ask({"id": v["id"], "input": v["input"]}, t_out)
    except TimeoutError:
        return Record(v["id"], v["size"], v["tags"], "timeout", None, message=f"> {t_out:g}s")
    except SolverDied as e:
        return Record(v["id"], v["size"], v["tags"], "crash", None, message=str(e))
    rss = solver.rss_kb()
    if ans.get("id") != v["id"]:
        return Record(v["id"], v["size"], v["tags"], "error", wall, rss,
                      f"answer id {ans.get('id')!r} != {v['id']!r}")
    if "error" in ans:
        return Record(v["id"], v["size"], v["tags"], "error", wall, rss, str(ans["error"]))
    try:
        why = gen.verify(v, ans.get("output"))
    except Exception as e:  # noqa: BLE001 — a malformed answer must not stop the run
        why = f"verify raised {type(e).__name__}: {e}"
    return Record(v["id"], v["size"], v["tags"], "ok" if why is None else "wrong", wall, rss,
                  why or "", extra=ans.get("extra"))


def machine() -> dict:
    """Facts about the machine the timings were measured on."""
    info = {"python": platform.python_version(), "kernel": platform.release(),
            "machine": platform.machine(), "image": os.environ.get("CA_IMAGE", "?"),
            "cpus_visible": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity")
            else os.cpu_count(), "cpu_count": os.cpu_count()}
    try:
        for ln in Path("/proc/cpuinfo").read_text().splitlines():
            if ln.startswith("model name"):
                info["cpu"] = ln.split(":", 1)[1].strip()
                break
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ln.startswith("MemTotal"):
                info["mem_total_kb"] = int(ln.split()[1])
                break
    except OSError:
        pass
    gov = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    info["governor"] = gov.read_text().strip() if gov.exists() else "n/a (not exposed)"
    try:
        info["loadavg_1m"] = os.getloadavg()[0]
    except OSError:
        pass
    return info


def build(cap: Capstone, log=print) -> None:
    if cap.build:
        log(f"build: {cap.build}")
        subprocess.run(["sh", "-c", cap.build], cwd=cap.dir, check=True)


def bench(cap: Capstone, sizes: list[str] | None = None, limit: int | None = None,
          out: Path | None = None, log=print) -> Path:
    """Run the reference over the size classes; write the raw run (default
    ``build/capstone/<slug>/raw.json``) for ``report``."""
    build(cap, log)
    t0 = time.time()
    log(f"bench {cap.slug}: {cap.command}")
    recs = run(cap, cap.command, cap.dir, sizes, limit, log=log)
    raw = {"capstone": cap.slug, "command": cap.command, "started": int(t0),
           "duration_s": round(time.time() - t0, 3), "machine": machine(),
           "sizes": [s.name for s in cap.sizes if not sizes or s.name in sizes],
           "records": [asdict(r) for r in recs]}
    out = out or cap.dir.parents[2] / "build" / "capstone" / cap.slug / "raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"raw results: {out}")
    return out


def check(cap: Capstone, command: str, cwd: Path, sizes: list[str] | None = None,
          limit: int | None = None, log=print) -> bool:
    """Instructor's defence-time check of a submission: correctness and time per vector,
    compared with the reference time x slack of ``bench/results.json`` when present."""
    res_path = cap.bench_dir / "results.json"
    limits = {}
    if res_path.exists():
        res = json.loads(res_path.read_text(encoding="utf-8"))
        limits = {k: v.get("limit_s") for k, v in (res.get("summary") or {}).items()}
    log(f"check {cap.slug}: {command} (in {cwd})")
    recs = run(cap, command, cwd, sizes, limit, log=log)
    ok_all = True
    log(f"\n{'size':<10} {'ok':>6} {'max, s':>10} {'limit, s':>10}  verdict")
    for name in dict.fromkeys(r.size for r in recs):
        rs = [r for r in recs if r.size == name]
        n_ok = sum(r.status == "ok" for r in rs)
        tmax = max((r.wall_s for r in rs if r.wall_s is not None), default=None)
        lim = limits.get(name)
        good = n_ok == len(rs) and (lim is None or (tmax is not None and tmax <= lim))
        ok_all &= good
        log(f"{name:<10} {n_ok:>3}/{len(rs):<2} "
            f"{'-' if tmax is None else f'{tmax:10.3f}':>10} {'-' if lim is None else f'{lim:10.3g}':>10}"
            f"  {'PASS' if good else 'FAIL'}")
    return ok_all
