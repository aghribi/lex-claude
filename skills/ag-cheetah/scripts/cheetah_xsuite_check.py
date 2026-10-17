"""Cross-check Cheetah against Xsuite on a drift-quad-drift cell.

Tracks the same electrons through both codes and compares final coordinates.
Conversions (Cheetah -> Xsuite): x, px, y, py unchanged; zeta = -beta0 * tau; ptau = p.

Usage: python cheetah_xsuite_check.py [--k1 5] [--shift-x 1e-4] [--energy 1e8] [--amp 1e-4]
"""

import argparse

import cheetah
import numpy as np
import torch
import xtrack as xt

torch.set_default_dtype(torch.float64)  # Cheetah defaults to float32; mixed dtypes fail in tracking

p = argparse.ArgumentParser()
p.add_argument("--energy", type=float, default=1e8, help="total energy [eV]")
p.add_argument("--k1", type=float, default=5.0, help="quad strength [1/m^2]")
p.add_argument("--lq", type=float, default=0.2, help="quad length [m]")
p.add_argument("--ld", type=float, default=1.0, help="drift length [m]")
p.add_argument("--shift-x", type=float, default=0.0, help="quad offset in x [m]")
p.add_argument("--amp", type=float, default=1e-4, help="coordinate amplitude")
p.add_argument("--n", type=int, default=200)
p.add_argument("--method", default="drift_kick_drift", choices=["linear", "second_order", "drift_kick_drift"], help="Cheetah tracking method for all elements")
p.add_argument("--no-espread", action="store_true", help="set p = 0 (isolates chromatic terms)")
p.add_argument("--tol", type=float, default=1e-6, help="tolerance relative to amp")
a = p.parse_args()

rng = np.random.default_rng(0)
coords = rng.uniform(-a.amp, a.amp, size=(a.n, 6))  # x, px, y, py, tau, p (Cheetah)
coords[:, 5] *= 0 if a.no_espread else 10  # energy spread an order larger

# Cheetah
particles = torch.ones(a.n, 7, dtype=torch.float64)
particles[:, :6] = torch.from_numpy(coords)
beam = cheetah.ParticleBeam(particles, energy=torch.tensor(a.energy), dtype=torch.float64)
seg = cheetah.Segment(
    [
        cheetah.Drift(length=torch.tensor(a.ld), tracking_method=a.method),
        cheetah.Quadrupole(
            length=torch.tensor(a.lq),
            k1=torch.tensor(a.k1),
            misalignment=torch.tensor([a.shift_x, 0.0]),
            tracking_method=a.method,
            num_steps=50,
            dtype=torch.float64,
        ),
        cheetah.Drift(length=torch.tensor(a.ld), tracking_method=a.method),
    ]
)
out = seg.track(beam)
ch = out.particles[:, :6].numpy()
beta0 = float(beam.relativistic_beta)

# Xsuite
line = xt.Line(
    elements=[
        xt.Drift(length=a.ld),
        xt.Quadrupole(length=a.lq, k1=a.k1, shift_x=a.shift_x),
        xt.Drift(length=a.ld),
    ],
    element_names=["d1", "q", "d2"],
)
line.particle_ref = xt.Particles(mass0=xt.ELECTRON_MASS_EV, q0=-1, energy0=a.energy)
line.build_tracker()
part = line.build_particles(
    x=coords[:, 0], px=coords[:, 1], y=coords[:, 2], py=coords[:, 3],
    zeta=-beta0 * coords[:, 4], ptau=coords[:, 5],
)
line.track(part)
order = np.argsort(part.particle_id)
xs = np.column_stack(
    [part.x[order], part.px[order], part.y[order], part.py[order],
     -part.zeta[order] / beta0, part.ptau[order]]
)

names = ["x", "px", "y", "py", "tau", "p"]
worst = 0.0
print(f"E={a.energy:.3g} eV  beta0={beta0:.9f}  k1={a.k1}  shift_x={a.shift_x}  amp={a.amp}")
for i, n in enumerate(names):
    d = np.max(np.abs(ch[:, i] - xs[:, i]))
    worst = max(worst, d / a.amp)
    print(f"  {n:>4}: max|cheetah - xsuite| = {d:.3e}")
print(f"worst / amp = {worst:.2e}  ->  {'PASS' if worst < a.tol else 'FAIL'} (tol {a.tol:g})")
raise SystemExit(0 if worst < a.tol else 1)
