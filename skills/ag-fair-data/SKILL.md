---
name: ag-fair-data
description: Make research data FAIR (findable, accessible, interoperable, reusable) - choose formats (Parquet, HDF5, openPMD, NeXus, Zarr, NetCDF), write loaders with explicit dtypes and units, attach metadata, handle machine time series (archivers, logs), build ML data pipelines (PyTorch datasets, Petastorm), and prepare dataset releases (Zenodo, DataCite, persistent identifiers). Use when loading, converting, storing, documenting or publishing data, designing a dataset for training, or when the user mentions FAIR, metadata, ontologies, data management plans or EU open-science requirements.
---

Data from accelerators, simulations and training runs, made reusable by someone who was not in the room. Library versions checked on PyPI in October 2026: pyarrow 26, polars 2.0, pandas 3.0, h5py 3.16, zarr 3.4, xarray 2026.9, netCDF4 1.7, openPMD-api 0.17, openpmd-beamphysics 0.16, petastorm 0.13.1 (last release January 2026). Check installed versions before relying on an API.

## Step 1. Inventory before code

For each data source, write down in 5 lines: what it is (measurement, simulation, derived), producer and version, shape and size, units of every column or dataset, time base and time zone. Ask the user for anything unknown; never guess units.

## Step 2. Pick the format by data shape

| Data | Format | Why |
|---|---|---|
| Tables (scans, logs, results, episode summaries) | **Parquet** (pyarrow, polars) | Typed columns, compression, schema metadata, fast column reads |
| N-d arrays, images, waveforms, nested groups | **HDF5** (h5py) | Attributes on every group and dataset; standard in facilities |
| Particle distributions | **openPMD** (HDF5) | Community standard; Cheetah reads and writes it (`ParticleBeam.from_openpmd_file`, `save_as_openpmd_h5`), openpmd-beamphysics too |
| Facility experiment data | **NeXus** (HDF5) when the facility uses it | Shared with photon/neutron facilities |
| Large chunked arrays, cloud or parallel writes | **Zarr** | Chunked, object-store friendly |
| Gridded labelled data (maps vs time and position) | **NetCDF** via xarray | Coordinates and units as first-class metadata |
| Small exchange files only | CSV | Never as primary storage: no types, no units |

## Step 3. Loaders

- Explicit schema on read: dtypes for every column (`pl.read_csv(..., schema=...)`, `pd.read_csv(dtype=...)`). Fail loudly on unexpected columns.
- Units travel with the data: Parquet schema metadata or column names with units (`sigma_x_m`); HDF5 `units` attribute on each dataset. Convert at the boundary, once, through one function.
- polars for anything large or slow in pandas; pandas for small interactive work (`.loc`, no chained assignment).
- Never drop NaN, duplicates or outliers silently: count, report, and keep the rule in code.
- Record provenance in the file: source path or PV names, producer code and version, git SHA, creation time (UTC), parameters.

## Step 4. Machine time series (archivers, logs, e-logs)

- Timestamps time-zone aware, stored in UTC; keep the source time zone in metadata.
- Irregular sampling is the norm: resample explicitly (`group_by_dynamic` in polars, `resample` in pandas) and state the rule (mean, last, interpolate). No silent forward-fill across gaps; mark gaps.
- Align channels on a common time base before computing anything across them; record the alignment tolerance.
- Keep raw data immutable; derived data in a separate file that names its inputs.

## Step 5. ML pipelines

- Single node: a `torch.utils.data.Dataset` over Parquet (pyarrow row groups) or HDF5 (open per worker, not in `__init__`, so multiprocessing works).
- Spark or very large Parquet: Petastorm (`make_reader` / `make_batch_reader` with its PyTorch `DataLoader`). It is maintained but slow-moving; check compatibility with the installed pyarrow first.
- Split train / validation / test by time or by machine run, never randomly across correlated samples; save the split definition with the data.
- Version datasets (content hash or DOI), and log the dataset version with every training run.

## Step 6. Metadata and vocabularies

- Each dataset gets a README (what, who, when, how produced, units, license, how to cite) and machine-readable metadata.
- Use existing vocabularies and say which: DataCite (release metadata), Dublin Core / schema.org (general description), openPMD and NeXus (domain structure). Do not invent an ontology; if a domain term has no standard, define it once in a glossary file and reuse it.
- Licenses: CC-BY 4.0 for data, an OSI license for code, unless the project's grant agreement says otherwise.

## Step 7. Release

- Deposit in a repository that mints DOIs (Zenodo or the institution's); link the DOI in papers and deliverables.
- EU projects: follow the project's data management plan; every released dataset maps to a DMP entry and, where relevant, a deliverable ID (see the EU traceability rule).
- Check before release: opens with a fresh environment, units documented, no personal data, license set, citation text present.

## Checks to run on any data file

- Open it in a clean environment and print schema or tree, units and metadata.
- Row or element counts match the source; min/max of key columns are physically plausible (use `uncertainty-and-units` when in doubt).
- Round trip: write, read, compare.
