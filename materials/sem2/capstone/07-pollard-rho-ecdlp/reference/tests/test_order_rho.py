"""ord(P) and both rho variants of the reference vs Sage (P.order(), discrete_log)."""

import json
import random
import subprocess
import sys

import pytest
from conftest import REF, sage_curve, sage_point, xy

from rho_ecdlp.ec import Curve
from rho_ecdlp.order import point_order
from rho_ecdlp.rho import Rho, RhoFailure
from rho_ecdlp.solver import handle, handle_safe


@pytest.mark.parametrize("bits", [6, 9, 12, 20, 32, 40, 48])
@pytest.mark.parametrize("shape", ["random", "a0", "b0"])
def test_order_vs_sage(rng, bits, shape):
    for _ in range(8):
        S, p, a, b = sage_curve(rng, bits, a=0 if shape == "a0" else None,
                                b=0 if shape == "b0" else None)
        if p <= 3:
            continue
        P = sage_point(S, rng)
        if rng.getrandbits(1):              # sometimes a point of a smaller order
            P = int(S.order() // max(S.order().factor())[0]) * P
        if P.is_zero():
            continue
        n, _ = point_order(Curve.checked(p, a, b), xy(P))
        assert n == P.order()


def _instance(rng, bits, shape="prime"):
    """(S, p, a, b, P, n) with n = ord(P) of `bits` bits, P in a prime subgroup unless
    shape == "composite" (then P is a random point, n = its order)."""
    from sage.all import factor

    while True:
        S, p, a, b = sage_curve(rng, bits + (rng.randrange(1, 4) if shape == "cofactor" else 0),
                                a=0 if shape == "a0" else None)
        N = int(S.order())
        P = sage_point(S, rng)
        if shape == "composite":
            n = int(P.order())
            if n.bit_length() == bits and len(factor(n)) > 1:
                return S, p, a, b, P, n
            continue
        q = int(max(factor(N))[0])
        if q.bit_length() == bits and (shape != "cofactor" or q < N):
            P = (N // q) * P
            if not P.is_zero():
                return S, p, a, b, P, q


def _req(p, a, b, P, Q, n, method, **kw):
    return {"p": p, "a": a, "b": b, "P": list(xy(P)), "Q": None if Q.is_zero() else list(xy(Q)),
            "n": n, "method": method, **kw}


@pytest.mark.parametrize("method", ["floyd", "dp"])
@pytest.mark.parametrize("shape", ["prime", "cofactor", "a0", "composite"])
@pytest.mark.parametrize("bits", [8, 16, 24])
def test_dlog_vs_sage(rng, method, shape, bits):
    from sage.all import discrete_log

    for _ in range(4):
        S, p, a, b, P, n = _instance(rng, bits, shape)
        x = rng.randrange(n)
        Q = x * P
        out, extra = handle(_req(p, a, b, P, Q, n, method))
        assert out["x"] == discrete_log(Q, P, n, operation="+") == x
        assert extra["verified"] and extra["n"] == n


@pytest.mark.parametrize("method", ["floyd", "dp"])
def test_special_q(rng, method):
    S, p, a, b, P, n = _instance(rng, 20)
    for x in (0, 1, n - 1, 2):
        out, _ = handle(_req(p, a, b, P, x * P, n, method))
        assert out["x"] == x


def test_floyd_record_has_the_congruence(rng):
    S, p, a, b, P, n = _instance(rng, 20)
    x = rng.randrange(n)
    _, extra = handle(_req(p, a, b, P, x * P, n, "floyd"))
    last = extra["attempts"][-1]
    al, be, ga, de = (last[k] for k in ("alpha", "beta", "gamma", "delta"))
    E = Curve.checked(p, a, b)
    # the collision: [al]P + [be]Q = [ga]P + [de]Q, and x solves (be - de) x = ga - al
    assert E.lin(al, xy(P), be, xy(x * P)) == E.lin(ga, xy(P), de, xy(x * P)) == tuple(last["collision"])
    c = last["congruence"]
    assert (c["u"] - (be - de)) % n == 0 and (c["v"] - (ga - al)) % n == 0
    assert x in last["solutions"] and (c["u"] * x - c["v"]) % n == 0


def test_given_start_and_determinism(rng):
    S, p, a, b, P, n = _instance(rng, 20)
    Q = rng.randrange(n) * P
    req = _req(p, a, b, P, Q, n, "floyd", start=[5, 7])
    out1, ex1 = handle(req)
    out2, ex2 = handle(req)
    assert ex1 == ex2 and out1 == out2
    assert ex1["attempts"][0]["start"] == [5, 7]
    assert tuple(ex1["attempts"][0]["start_point"]) == xy(5 * P + 7 * Q)
    _, ex3 = handle({**req, "seed": 1})
    _, ex4 = handle({**req, "seed": 1, "method": "dp"})
    assert ex3["seed"] == 1 and ex4["method"] == "dp"


def test_max_iter_exceeded(rng):
    S, p, a, b, P, n = _instance(rng, 24)
    Q = rng.randrange(n) * P
    for method in ("floyd", "dp"):
        ans = handle_safe(_req(p, a, b, P, Q, n, method, max_iter=5, max_attempts=2))
        assert "max_iter" in ans["error"]


def test_degenerate_collision_retries():
    # n tiny: the congruence is often degenerate (u = 0 mod n): it must still solve
    rng = random.Random(3)
    for _ in range(30):
        S, p, a, b, P, n = _instance(rng, 3)
        x = rng.randrange(n)
        for method in ("floyd", "dp"):
            out, ex = handle(_req(p, a, b, P, x * P, n, method))
            assert out["x"] == x


def test_q_not_in_subgroup_fails_cleanly(rng):
    while True:
        S, p, a, b, P, n = _instance(rng, 12, "cofactor")
        R = sage_point(S, rng)
        if n * R != 0:                      # R is not in <P>
            break
    ans = handle_safe(_req(p, a, b, P, R, n, "floyd", max_attempts=3))
    assert "no valid solution" in ans["error"]


def test_wrong_n_rejected(rng):
    S, p, a, b, P, n = _instance(rng, 16)
    ans = handle_safe(_req(p, a, b, P, P, n + 1, "floyd"))
    assert "not a multiple of ord(P)" in ans["error"]


def test_n_computed_when_absent(rng):
    S, p, a, b, P, n = _instance(rng, 20, "cofactor")
    Q = 12345 * P
    req = _req(p, a, b, P, Q, n, "dp")
    del req["n"]
    out, extra = handle(req)
    assert extra["n_source"] == "computed" and extra["n"] == n and out["x"] == 12345 % n


def test_cli_contract(rng):
    S, p, a, b, P, n = _instance(rng, 16)
    Q = 77 * P
    proc = subprocess.Popen([sys.executable, str(REF / "main.py")], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, text=True)
    reqs = [{"id": "a", "input": _req(p, a, b, P, Q, n, "floyd")},
            {"id": "b", "input": {"op": "order", "p": p, "a": a, "b": b, "P": list(xy(P))}},
            {"id": "c", "input": {"p": p, "a": a, "b": b, "P": [1, 1], "Q": None, "n": 2}},
            {"id": "d", "input": {"op": "nope", "p": p, "a": a, "b": b, "P": list(xy(P))}}]
    answers = []
    for r in reqs:          # one line in, one line out (the solver flushes every answer)
        proc.stdin.write(json.dumps(r) + "\n")
        proc.stdin.flush()
        answers.append(json.loads(proc.stdout.readline()))
    proc.stdin.write("not json\n")
    proc.stdin.close()
    answers.append(json.loads(proc.stdout.readline()))
    assert proc.wait(timeout=10) == 0
    assert [x["id"] for x in answers] == ["a", "b", "c", "d", None]
    assert answers[0]["output"] == {"x": 77 % n} and answers[0]["extra"]["verified"]
    assert answers[1]["output"] == {"n": n}
    assert all("error" in x for x in answers[2:])


def test_generator_vectors_and_verify():
    """The capstone's own vectors (taskgen generator) are solved; verify rejects wrong x."""
    from taskgen.capstone.gens import pollard_rho_ecdlp as gen

    rng = random.Random(7)
    kinds = list(gen.KINDS)
    for method in ("floyd", "dp"):
        for kind in kinds:
            v = gen.generate({"bits": 16, "method": method, "kinds": [kind]}, rng)
            out, _ = handle(v["input"])
            assert gen.verify(v, out) is None
            assert gen.verify(v, {"x": out["x"] + 1}) is not None
            assert gen.verify(v, {"x": out["x"] + v["input"]["n"]}) is None   # any x = x0 mod n
    for kind in ("prime", "cofactor", "a0", "b0", "composite"):
        v = gen.generate({"op": "order", "p_bits": 24, "kinds": [kind]}, rng)
        out, _ = handle(v["input"])
        assert gen.verify(v, out) is None and gen.verify(v, {"n": out["n"] * 2}) is not None
