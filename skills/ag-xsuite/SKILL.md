---
name: ag-xsuite
description: Write, debug and validate code using Xsuite (xtrack, xpart, xobjects, xfields, xdeps, xcoll, xwakes) - building lines with Environment, MAD-X/MAD-NG import, twiss, knobs and matching, tracking, particle coordinates, JSON lattices, and cross-checks with Cheetah or other codes. Use whenever code imports xtrack/xpart/xsuite, for lattice optics, tune or orbit matching, multi-turn tracking, or when converting lattices from MAD-X.
---

Written against **xtrack 0.95.0** (xpart 0.23.2, xobjects 0.5.6, xfields 0.25.5, xdeps 0.10.8, xcoll 0.6.8; the pipx `xsuite` env) and verified by running `scripts/xsuite_smoke.py`. Xsuite moves fast (PyPI was at xtrack 0.118 in October 2026): check `uv pip show xtrack` and read the installed source before using anything below on another version.

## Particle coordinates (from the 0.95 source, `xtrack/particles/particles.py`)

| Field | Definition | Unit |
|---|---|---|
| `x`, `y` | position | m |
| `px`, `py` | `Px / (m/m0 · p0c)` | 1 |
| `zeta` | `s - beta0 c t` | m |
| `tau` | `s / beta0 - c t` | m |
| `delta` | `(P c m0/m - p0c) / p0c` | 1 |
| `ptau` | `(E m0/m - E0) / p0c` | 1 |
| `pzeta` | `ptau / beta0` | 1 |
| `p0c`, `energy0`, `mass0` | reference momentum, total energy, rest mass | eV |
| `q0` | reference charge | e |
| `state` | `<= 0` lost, `> 0` alive | |

Set exactly one of `delta`, `ptau`, `pzeta`; the others are derived. Electrons: `xt.Particles(mass0=xt.ELECTRON_MASS_EV, q0=-1, energy0=...)`. Conversion to and from Cheetah: see the `ag-cheetah` skill (verified to 1.6e-7 relative).

## Verified workflow (all steps pass on 0.95.0)

```python
import xtrack as xt
env = xt.Environment()
env["kq"] = 0.5                                   # knob
line = env.new_line(components=[
    env.new("qf", xt.Quadrupole, length=0.5, k1="kq", at=0.25),
    env.new("qd", xt.Quadrupole, length=0.5, k1="-kq", at=5.25),
])                                                # drifts inserted from `at`
line.particle_ref = xt.Particles(mass0=xt.ELECTRON_MASS_EV, q0=-1, energy0=1e9)
tw = line.twiss(method="4d")                      # 4d: no RF / longitudinal motion
tw.qx, tw.betx, tw.dx
env["kq"] = 0.55                                  # knobs update the line live
line.match(method="4d", vary=xt.VaryList(["kq", "kqd"], step=1e-6),
           targets=xt.TargetSet(qx=0.20, qy=0.18, tol=1e-8))
line.to_json("line.json"); xt.Line.from_json("line.json")
p = line.build_particles(x=[1e-3], px=[0.0]); line.track(p, num_turns=100)
```

## MAD-X and MAD-NG

- **Native parser, no cpymad needed:** `env = xt.load("file.madx")`, then `line = env["sequence_name"]`. `:=` expressions become knobs. Checked: a FODO cell loaded from MAD-X gives the same tune as the Python-built one (0.20633), and changing the knob moves it as expected. Sample: `scripts/fodo.madx`.
- `xt.load` formats: json, madx, python, csv, hdf5, tfs.
- Legacy path: `xt.Line.from_madx_sequence(madx.sequence.name, ...)` needs `cpymad` (not installed in the pipx env).
- MAD-NG: `xtrack/madng_interface.py` exists in 0.95; read it before use, and validate optics against MAD-NG's own twiss.

## Gotchas

- **`method="4d"`** for lines without RF. The default 6D twiss raises `ValueError: Invalid one-turn map: No coordinates respond to variations of zeta` (checked on 0.95.0).
- **`particle_ref` first.** Twiss and `build_particles` need it; set it right after building the line.
- **Kernels compile on first use** (`Compiling ContextCpu kernels...`, tens of seconds). Not a hang. Reuse the line and tracker; `line.discard_tracker()` before structural edits.
- **Lost particles stay in arrays.** Filter on `state > 0`; order by `particle_id` before comparing with another code (tracking can reorder).
- **Element misalignment** is `shift_x`, `shift_y`, `shift_s` (m) and `rot_s_rad`, `rot_x_rad`, `rot_y_rad` on the element. Same sign as Cheetah's `misalignment` for the x shift (checked).
- **Units in imported lattices** follow MAD-X (energy in GeV in the `beam` command, `k1` in 1/m²). State them at every interface.

## Validation habit

1. Run `scripts/xsuite_smoke.py` after an Xsuite upgrade: one line per API step, PASS/FAIL.
2. Record `xt.__version__` with every result.
3. Compare new lattices against the source code's own optics (MAD-X/MAD-NG twiss) at a few locations: tunes, beta functions, dispersion, within a stated tolerance.
