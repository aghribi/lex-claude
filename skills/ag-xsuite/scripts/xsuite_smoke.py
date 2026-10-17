"""Smoke test of the Xsuite API surface used by the ag-xsuite skill.

Builds a FODO ring with a knob, runs a 4D twiss, matches the tunes, round-trips
the line through JSON and tracks particles. Prints PASS/FAIL per step.

Usage: python xsuite_smoke.py
"""

import json
import os
import tempfile

import numpy as np
import xtrack as xt

results = []


def check(name, fn):
    try:
        info = fn()
        results.append((name, True, info))
    except Exception as e:  # report and keep going: this is a probe of the API
        results.append((name, False, f"{type(e).__name__}: {e}"))


env = xt.Environment()
env["kq"] = 0.5
env["lcell"] = 10.0


def build():
    cell = env.new_line(
        components=[
            env.new("qf", xt.Quadrupole, length=0.5, k1="kq", at=0.25),
            env.new("d1", xt.Drift, length=4.5),
            env.new("qd", xt.Quadrupole, length=0.5, k1="-kq", at=5.25),
            env.new("d2", xt.Drift, length=4.5),
        ]
    )
    return cell


cell = None


def step_build():
    global cell
    cell = build()
    cell.particle_ref = xt.Particles(mass0=xt.ELECTRON_MASS_EV, q0=-1, energy0=1e9)
    return f"length={cell.get_length():.3f} m, elements={len(cell.element_names)}"


def step_twiss():
    tw = cell.twiss(method="4d")
    return f"qx={tw.qx:.5f} qy={tw.qy:.5f} betx_max={tw.betx.max():.3f} m"


def step_knob():
    q0 = cell.twiss(method="4d").qx
    env["kq"] = 0.55
    q1 = cell.twiss(method="4d").qx
    env["kq"] = 0.5
    assert q1 != q0
    return f"kq 0.50->0.55 moves qx {q0:.5f}->{q1:.5f}"


def step_match():
    env.vars["kqd"] = 0.5
    cell["qd"].k1 = "-kqd"
    opt = cell.match(
        method="4d",
        vary=xt.VaryList(["kq", "kqd"], step=1e-6),
        targets=xt.TargetSet(qx=0.20, qy=0.18, tol=1e-8),
    )
    tw = cell.twiss(method="4d")
    assert abs(tw.qx - 0.20) < 1e-6 and abs(tw.qy - 0.18) < 1e-6
    return f"kq={env['kq']:.6f} kqd={env['kqd']:.6f} -> qx={tw.qx:.6f} qy={tw.qy:.6f}"


def step_table():
    t = cell.get_table()
    return f"columns include: {[c for c in ('name', 's', 'element_type') if c in t._col_names]}"


def step_json():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "cell.json")
        cell.to_json(path)
        line2 = xt.Line.from_json(path)
        line2.particle_ref = cell.particle_ref.copy()
        tw1, tw2 = cell.twiss(method="4d"), line2.twiss(method="4d")
        assert np.isclose(tw1.qx, tw2.qx, atol=1e-10)
        size = os.path.getsize(path)
    return f"round trip keeps qx, json {size} bytes"


def step_track():
    p = cell.build_particles(x=np.linspace(-1e-3, 1e-3, 11), px=0.0)
    cell.track(p, num_turns=100)
    lost = int(np.sum(p.state <= 0))
    return f"100 turns, lost={lost}, at_turn={int(p.at_turn.max())}"


for name, fn in [("build line from Environment", step_build), ("twiss 4d", step_twiss),
                 ("knob via env vars", step_knob), ("match tunes", step_match),
                 ("get_table", step_table), ("json round trip", step_json),
                 ("track 100 turns", step_track)]:
    check(name, fn)

print(f"xtrack {xt.__version__}")
for name, ok, info in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {info}")
raise SystemExit(0 if all(ok for _, ok, _ in results) else 1)
