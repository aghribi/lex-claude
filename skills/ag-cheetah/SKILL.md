---
name: ag-cheetah
description: Write, debug and validate code using Cheetah (cheetah-accelerator, PyTorch beam dynamics) - lattices (Segment, Quadrupole, Drift, Screen, CombinedCorrector), beams (ParameterBeam, ParticleBeam), tracking methods, gradients and batched simulation, RL environments for accelerator tuning, and conversion to/from Xsuite, Ocelot, Bmad, Elegant, openPMD. Use whenever code imports cheetah, for RL beam-tuning environments, or when comparing Cheetah with another tracking code.
---

Written against **cheetah-accelerator 0.8.0** (the RL4AA venv) and verified by running code, not from memory. Before relying on anything below, check the installed version (`uv pip show cheetah-accelerator`) and read its source in site-packages when the version differs or a signature is in doubt.

## Coordinates and units (from the 0.8.0 source)

Particle vector is 7D: `(x, px, y, py, tau, p, 1)`.

| Quantity | Definition | Unit |
|---|---|---|
| `x`, `y` | position | m |
| `px`, `py` | `P_x / P_0`, `P_y / P_0` | 1 |
| `tau` | `c t - s / beta0` (particle ahead has negative `tau`) | m |
| `p` | `ΔE / (p0 c)` | 1 |
| `energy` | **total** reference energy (`gamma = energy / mass_eV`) | eV |
| `k1` | quadrupole strength | 1/m² |
| `angle` (dipole, correctors) | deflection | rad |
| `misalignment` | `(dx, dy)` of the element | m |
| `voltage`, `phase`, `frequency` (Cavity) | | V, degrees, Hz |

Species defaults to electron. `Dipole.gap` is the full gap: MAD/Elegant `HGAP = gap / 2`.

## Conversion to Xsuite (verified)

| Cheetah | Xsuite |
|---|---|
| `x, px, y, py` | same |
| `tau` | `-zeta / beta0` (Xsuite `zeta = s - beta0 c t`) |
| `p` | `ptau` (same quantity, `ΔE / p0c`) |
| `energy` | `energy0` (total, eV) |
| `misalignment[0]` | `shift_x`, same sign |

Cheetah has no Xsuite converter. Converters exist for Ocelot (`Segment.from_ocelot`), Bmad (`from_bmad`), Elegant (`from_elegant`), NX tables (`from_nx_tables`), Astra and openPMD beams (`ParticleBeam.from_openpmd_file`, `save_as_openpmd_h5`), and Cheetah's own JSON (`Segment.from_lattice_json` / `to_lattice_json`). Between Cheetah and Xsuite, write one documented conversion function and validate it.

**Validation script:** `scripts/cheetah_xsuite_check.py` tracks the same electrons through a drift-quad-drift cell in both codes. Measured with cheetah 0.8.0 / xtrack 0.95.0 at 100 MeV, amplitude 1e-4:

| Cheetah `tracking_method` | Agreement (worst / amplitude) |
|---|---|
| `drift_kick_drift` on every element | 1.6e-7, with or without quad offset |
| `linear` | 4.7e-3 with energy spread; 5.9e-4 without |

`linear` is exact for linear transverse optics (1e-19 at zero energy spread) but omits chromatic terms (∝ px·δ·L) and path lengthening in `tau` (∝ px²·L). Use `drift_kick_drift` when comparing with full tracking or when energy spread or large amplitudes matter; keep `linear` for fast RL training and say so.

## Gotchas (each one observed)

- **dtype.** Cheetah defaults to float32. One float32 tensor (for example a `misalignment` built with `torch.tensor([...])`) inside a float64 beam crashes tracking with `expected m1 and m2 to have the same dtype`. Pass `dtype=` everywhere, or `torch.set_default_dtype(torch.float64)` at the top of validation code.
- **Silent beam defaults.** `ParameterBeam.from_parameters()` fills anything not given: `energy=1e8` eV, `sigma_x=sigma_y=175e-6` m, `sigma_px=sigma_py=4e-6`. Always pass every parameter that matters.
- **Inactive diagnostics.** `Screen` and `BPM` record only with `is_active = True`; read with `screen.get_read_beam()`. A screen with `is_blocking=True` stops the beam.
- **Element access by name** (`segment.cla_s04_mag_quad_01`) works only for valid Python names; otherwise `DirtyNameWarning`. Use `sanitize_name=True` or `segment.element_names` / `element_index`.
- **Importer warnings are physics warnings.** `UnknownElementWarning`, `NotUnderstoodPropertyWarning`, `DefaultParameterWarning` mean the lattice is not what the source file says. Never silence them in a validation run; list them.
- **Setting strengths in RL envs.** Assign tensors with the segment's dtype (`torch.tensor(v, dtype=torch.float32)`), not Python floats.

## RL environment pattern (as in rl4aa26-challenge `src/environments/clara.py`)

- Lattice: `Segment.from_lattice_json(path)`; activate the screen; actions write `k1` and corrector angles; observation from `screen.get_read_beam()` (`mu_x, sigma_x, mu_y, sigma_y`).
- Domain randomisation: sample the incoming beam (energy, offsets, sizes) and quad misalignments each `reset`.
- Check that every sampled dimension is applied. In that repo the misalignment space has 8 dimensions but only 6 are applied (3 quads × 2); the last 2 are sampled and ignored.
- Off-screen beam: the env returns fixed sentinel values. Any reward built on them must be checked for exploitation (an agent can learn to push the beam off screen).

## Gradients and batching

Elements and beams are `torch.nn.Module`s: element attributes can be `torch.nn.Parameter` for gradient-based tuning or system identification. Tensors broadcast over leading batch dimensions, so a batch of `k1` values tracks many configurations in one call; check shapes of the outputs before reducing.

## Validation habit

1. Pin the version in the results metadata (`cheetah.__version__`).
2. Validate any new lattice against a reference (Xsuite, Ocelot or Elegant) with `drift_kick_drift`, and record the agreement.
3. Train on the fast model; evaluate the final policy on the full model before any claim.
