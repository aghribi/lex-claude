# Adastra (CINES, Montpellier): job submission reference

- Source: official user documentation, `https://dci.dci-gitlab.cines.fr/webextranet/` (abbreviated `DOC/` below).
- All pages read 2026-10-31, fetched with curl (HTTP 200), converted with pandoc. No login to any machine.
- Pages read: `DOC/index.html`, `DOC/quick_start/index.html`, `DOC/architecture/index.html`, `DOC/user_support/index.html`, `DOC/data_storage_and_transfers/index.html`, `DOC/data_visualization_and_analytics/index.html`, `DOC/software_stack/index.html`, `DOC/software_stack/cines_software_stack/venv_ai.html`, `DOC/software_stack/containers/index.html`, `DOC/software_stack/libraries/index.html`, `DOC/software_stack/tools/index.html`, `DOC/porting_optimization/index.html` (binding section), `DOC/other/faq_and_known_issues.html`, `DOC/other/changelogs.html`.
- Not read: the CINES user charter ("user policy governing the use of computer resources", linked from FAQ), eDARI, reser.cines.fr (needs an account).
- `[UNVERIFIED]` = inferred or not in docs. "Not documented" = searched, not found in pages read.

## 1. Machines

| Partition (`--constraint`) | Nodes | CPU | Accelerator | Memory/node | FP64 peak/node (host + device) |
|---|---|---|---|---|---|
| `GENOA` (scalar) | 544 | 2x AMD EPYC 9654 (Zen 4), 2x96 cores @ 2.4 GHz, no boost, SMT2 | none | 768 Gio DDR5-4800 (4 Gio/core) | 7.37 + 0 TFlop/s |
| `MI250` (accelerated) | 356 | 1x AMD EPYC 7A53 Trento (Zen 3), 64 cores @ 2.0 GHz, SMT2 | 4x MI250X (gfx90a, CDNA 2) = 8 GCDs, 64 Gio HBM2e per GCD | 256 Gio DDR4-3200 + 512 Gio HBM2e | 2.04 + 191.5 TFlop/s |
| `MI300` (accelerated APU) | 28 | 4x MI300A APU, 24 Zen 4 cores each = 96 cores @ 2.6 GHz | 4 GPUs (gfx942, CDNA 3, 228 CU each), one per APU | 512 Gio HBM3 shared CPU/GPU (128 Gio per APU) | 3.99 + 245.2 TFlop/s |
| `HPDA` (pre/post, visu) | 12 | 2x Genoa 96 cores @ 2.4 GHz | 2x NVIDIA L40 | 2048 Gio DDR5 | not documented |

- FP64 per MI250X GCD: 23.93 TFlop/s vector, no MFMA (47.86 with packed FP32 float2/float4). Per MI300A GPU: 61.3 TFlop/s vector.
- HBM throughput: 1.526 Tio/s per GCD (12.2 Tio/s per node); MI300A 4.96 Tio/s per APU, ~x0.75 of peak in practice.
- A GCD is seen as a separate GPU: 8 GPUs per MI250 node. Each MI300A shows as one GPU in `rocm-smi`.
- MI250 node: 4 NUMA domains, 16 cores each; CPU to GCD link 36 Go/s; 2 GCDs of one MI250X linked at 200 Go/s.
- Interconnect: Slingshot 200 Gb/s; 1 NIC per GENOA node, 4 NICs per MI250/MI300 node (GPU-direct RDMA).
- Login nodes: 10 front-end/transfer nodes, 2x EPYC 9654, 512 Gio, no GPU.
- OS: architecture page says RHEL 8.8, kernel 4.18; changelog dated 2026-02-13 says RedHat 9.6. The changelog is more recent: take RHEL 9.6 `[UNVERIFIED on machine]`.
- Doc inconsistencies: hardware list says MI300A "HBM2", partition table says HBM3. Scratch capacity given as 4.71 Pio (hardware list) and 1.9 Pio (storage page).

Sources: `DOC/architecture/index.html`, `DOC/other/changelogs.html`.

## 2. Accounts and accounting

- Access: eDARI account, join a project with Adastra hours, then request a machine account on eDARI (signed by requester, security representative, lab director). Logins are personal; no sharing.
- "Login unique": one login for all projects. `myproject -l` lists projects (the `--account` values are on the last line), `myproject -a <proj>` switches the active project, `myproject -c` shows directory variables, `${ACTIVE_PROJECT}` holds the active project.
- Charging units:

| Partition | Unit | Exclusive node-hour |
|---|---|---|
| MI250X | 1 whole MI250X = 2 GCDs | 4 MI250X hours |
| MI300A | 1 GPU device | 4 MI300A hours |
| GENOA | 1 core (2 hw threads) | 192 core hours |
| HPDA | not charged | |

- Doc warning: eDARI uses a whole MI250X as unit; "50 MI250X hours on eDARI = 100 MI250X GCD hours".
- `--constraint` decides what is charged. Time is charged as used, not as requested.
- Shared mode: minimum charge 8 cores (GENOA, MI250). On MI250, GCDs are allocated per 8 cores (15 cores asked = 2 GCDs charged). Charge = max of (memory fraction, core fraction, GPU fraction), rounded up to 8-core blocks:
  - GENOA: `CORES = CEIL8[ MAX(mem_asked/744*192 ; cores_asked) ]`
  - MI250: `GPUS = CEIL8[ MAX(mem_asked/232*64 ; cores_asked ; gpus_asked*8) ] / 8`
- 1 GCD in shared mode on MI250 = 0.5 MI250X hour per hour `[UNVERIFIED: derived from unit table + formula]`.
- Multi-node jobs always run exclusive and are billed for all allocated nodes.
- `sacct` CPU counts are hardware threads, not cores.
- Consumption: `myproject --state [project]`, `myproject -S`, `module load ccfr; ccfr_project`, https://reser.cines.fr/.
- Energy per job: `sacct --format=JobID,ElapsedRaw,ConsumedEnergyRaw,NodeList --jobs=<id>` (joules, node level).
- Refund for hardware-caused loss: ask svp@cines.fr.

Sources: `DOC/user_support/index.html` (#account-opening, #login-unique, #resource-consumption-and-charging-accounting), `DOC/data_storage_and_transfers/index.html` (CCFR module), `DOC/other/faq_and_known_issues.html`.

## 3. Slurm

### Mandatory and key options

| Option | Rule |
|---|---|
| `--account=<proj>` | mandatory |
| `--constraint=` | mandatory. `GENOA`, `MI250`, `MI300`, `HPDA` (options table lists only MI250, GENOA, HPDA; `MI300` appears in the MI300A example script) |
| `--time=` | mandatory, max 24 h (HPDA 6 h). Extension "on rare occasions" via svp@cines.fr |
| `--nodes=` | mandatory |
| `--exclusive` | whole nodes. Omitted with a sub-node request: job goes to the shared pool (`genoa-shared`, `mi250-shared` partitions) |
| `--gpus-per-node=` | required in shared mode on GPU partitions |
| `--ntasks-per-node`, `--cpus-per-task`, `--threads-per-core` | recommended in shared mode. Default threads-per-core is 2 (SMT) |
| `--mem=<N>G` | memory per node in shared mode; counts in the charge |
| `--qos` | do not set. QoS are not published; Slurm picks it from duration and size |
| `--gpu-srange=800-1500` | caps GPU clock (upper bound honoured) |

- No job size limit. Priority favours large jobs; fairshare on a 1-week sliding window; priority may be lowered for "thousands of small jobs".
- Shared mode: on some nodes of GENOA and MI250, all HPDA. Shared MI300A not documented. If the shared pool is full, exclusive may start sooner.
- Job arrays: max 11 jobs, else `AssocMaxSubmitJobLimit` (added 2025/12/02, "should be temporary").
- Use `srun`, not `mpirun`.
- Chaining: `sbatch --dependency=afterok:<jobid> next.sh`.
- Packing many small runs: one exclusive allocation plus `srun ... &` steps and `wait` (examples in docs).

### Binding and GPU affinity

- `srun` restricts ranks to hardware threads only; thread pinning needs `OMP_PROC_BIND`, `OMP_PLACES` (doc suggests `OMP_PROC_BIND=CLOSE`, `OMP_PLACES=THREADS`, `OMP_DISPLAY_AFFINITY=TRUE`).
- GPU: `--gpus-per-task=1 --gpu-bind=closest` with `--cpus-per-task=N` (both needed).
- MI250 recommended layout: 8 tasks x 8 cores x 1 GCD. Local rank to GCD/cores map: GCD0 48-55, GCD1 56-63, GCD2 16-23, GCD3 24-31, GCD4 0-7, GCD5 8-15, GCD6 32-39, GCD7 40-47.
- MI300A layout: 4 tasks x 24 cores x 1 GPU (cores 0-23, 24-47, 48-71, 72-95).
- Alternative: `srun --cpu-bind=none --mem-bind=none ./adastra_acc_binding.sh` (numactl + `ROCR_VISIBLE_DEVICES` script in docs). Binding makes most sense on whole nodes.
- Bad binding on MI300A with unified memory: x11 to x30 slowdown. Test with `hello_cpu_binding` / `hello_gpu_binding`.
- GPU-aware MPI: `export MPICH_GPU_SUPPORT_ENABLED=1` (+ `MPICH_GPU_MANAGED_MEMORY_SUPPORT_ENABLED=1` with `HSA_XNACK=1` on MI300A).

### Interactive

```bash
salloc --account=<proj> --constraint=MI250 --nodes=1 --time=1:00:00 --exclusive
srun --ntasks-per-node=8 --cpus-per-task=8 --threads-per-core=1 --gpus-per-task=1 --gpu-bind=closest -- <exe>
ssh <node>              # allowed on an allocated node
srun --pty -- "${SHELL}"
```

### Examples (from docs)

CPU, full GENOA node:
```bash
#!/bin/bash
#SBATCH --account=<proj>
#SBATCH --constraint=GENOA
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --time=1:00:00
module purge
module load cpe/24.07 craype-x86-genoa PrgEnv-cray
srun --ntasks-per-node=24 --cpus-per-task=8 --threads-per-core=1 -- <exe>
```

1 GCD (shared MI250 node, adapted from the docs' 2-task shared example and "Allocating a single GPU"):
```bash
#!/bin/bash
#SBATCH --account=<proj>
#SBATCH --constraint=MI250
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --threads-per-core=1
#SBATCH --time=1:00:00
module purge
module load cpe/24.07 craype-accel-amd-gfx90a craype-x86-trento PrgEnv-cray amd-mixed
srun --ntasks-per-node=1 --cpus-per-task=8 --threads-per-core=1 --gpus-per-task=1 --gpu-bind=closest -- <exe>
```

Full MI250 node (8 GCDs):
```bash
#!/bin/bash
#SBATCH --account=<proj>
#SBATCH --constraint=MI250
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --time=1:00:00
module purge
module load cpe/24.07 craype-accel-amd-gfx90a craype-x86-trento PrgEnv-cray amd-mixed
export MPICH_GPU_SUPPORT_ENABLED=1
srun --ntasks-per-node=8 --cpus-per-task=8 --threads-per-core=1 --gpus-per-task=1 --gpu-bind=closest -- <exe>
```

Full MI300A node: same with `--constraint=MI300`, `craype-accel-amd-gfx942 craype-x86-genoa`, `srun --ntasks-per-node=4 --cpus-per-task=24 ...`.

- Known issue 2025/08/20: `--threads-per-core` given to `salloc`/`sbatch` makes `srun` launch one rank with one core; give it to `srun`. The docs' own shared-mode examples still put it in `#SBATCH`. Check before relying on it `[UNVERIFIED whether still open]`.
- Known issue 2023/10/01: `srun: fatal: SLURM_MEM_PER_CPU, SLURM_MEM_PER_GPU, and SLURM_MEM_PER_NODE are mutually...` in shared allocations: add `srun --mem=0`.

Sources: `DOC/user_support/index.html` (#job-submission to #coredump-files), `DOC/quick_start/index.html`, `DOC/porting_optimization/index.html` (Proper binding, why and how), `DOC/other/faq_and_known_issues.html`, `DOC/software_stack/cines_software_stack/venv_ai.html`.

## 4. Storage (all Lustre; quotas per project group, except personal home)

| Area | Variable | Space / inodes | Backup | Purge | On compute nodes |
|---|---|---|---|---|---|
| Personal home | `${OWN_HOMEDIR}` (`/home/<login>`) | 20 Gio / 30 000 | yes (bacula) | never | read-write |
| Project home | `${HOMEDIR}`, `~`, `${SHAREDHOMEDIR}` | 100 Gio / 300 000 | yes | never | read-write |
| Scratch | `${SCRATCHDIR}`, `${SHAREDSCRATCHDIR}` | 20 Tio / 1 000 000 | no | 30 days after last access | read-write |
| Work | `${WORKDIR}`, `${SHAREDWORKDIR}` | 15 Tio / 250 000 | no | never | read-write |
| Store | `${STOREDIR}` | 1.5 Tio / 9 000 | yes (HSM, tape) | never | **not mounted** |

- Retention: 6 months after account deactivation or project end (non-purged areas). Projects last 1 year; data must be moved to the new project manually.
- Backups: daily, last 10 days (home, store); restore via svp@cines.fr.
- Quota check: `myproject -s <proj>`, `myproject -S`, `ccfr_quota`. Moving files between projects: `chgrp -R <projB>` or they count against project A.
- Store: tar archives before copying (HSM/tape, few large files). No need to compress.
- Prefix variables (`${<proj>_WORKDIR}`) are stable across `myproject -a`; recommended in scripts.
- `.bashrc`/`.bash_profile` in `${HOMEDIR}`; `.ssh` in `${OWN_HOMEDIR}`.
- Datasets: `${DSDIR}` (ImageNet1k, coco, pile, ...).
- Striping: `lfs setstripe -E 1G -c 1 -E 8G -c 8 -E -1 -c 24 <dir>` for large-file output dirs. Use `lfs find`.
- Copy between filesystems: `wdcp <src> <dst>` (runs as a job on transfer nodes; chain with `--dependency`).
- Core dumps go to `${SCRATCHDIR}/COREDIR/<jobid>/<host>` (`ulimit -c unlimited` is default; exclusive jobs only).

Sources: `DOC/data_storage_and_transfers/index.html`, `DOC/user_support/index.html` (#login-unique, #layout-of-common-files-and-directories, #coredump-files), `DOC/other/faq_and_known_issues.html`.

## 5. Network

- Login nodes: HTTP(S) through proxy `http://proxy-l-adastra.cines.fr:3128` (`http_proxy`/`https_proxy` set by default; `no_proxy` includes `.cines.fr`). Not the whole internet (VSCode note, "as of 2024/03"). Git hosts not authorized by the firewall: ask svp@cines.fr.
- Compute nodes: no internet access. Download models/data and build envs on login nodes; set `HF_HUB_OFFLINE=1` in jobs.
- Lab to Adastra transfers: initiate from the lab side; the reverse works only if the lab IP is allowed. (The doc refers to a "note just above" that is missing from the page.)
- CCFR network to IDRIS/TGCC: request access at svp@cines.fr, then `ssh adastra-ccfr.cines.fr` from a login node.
- FTP/RCP forbidden for transfers. Use scp, rsync, parallel-sftp.

Sources: `DOC/user_support/index.html` (#proxy), `DOC/quick_start/index.html`, `DOC/software_stack/tools/index.html` (VSCode), `DOC/software_stack/libraries/index.html` (HuggingFace, Boltz), `DOC/software_stack/cines_software_stack/venv_ai.html`, `DOC/data_storage_and_transfers/index.html`.

## 6. Containers

- Singularity/Apptainer binary available on compute nodes only, not on login nodes.
- Custom images: `container_submit.py <image> -P <project>` on a login node runs a CVE scan; if no critical CVE, image is placed in `/opt/software/containers/images/users/<project>/<name>.sif`. Critical CVE: mail with components, ticket at svp@cines.fr. Whether images may also run from user directories: not documented.
- AMD Infinity Hub images: `/opt/software/containers/images/infinity-hub/`.
- Documented run line (MI250 example):
  `singularity run --writable-tmpfs -B<input> -B/sys -B/dev -B/proc -B/lus /opt/software/containers/images/<c>.sif <exe>`
- ROCm-specific flag (`--rocm`): not documented. GPU access in the example comes from binding `/dev`, `/sys`, `/proc`.
- Container usage counts in the project home quota ("Cnt" line of `ccfr_project`).

Sources: `DOC/software_stack/containers/index.html`, `DOC/data_storage_and_transfers/index.html`.

## 7. Software

- Lmod. Always `module purge` first; load `cpe/XX.YY` before any other Cray module.
- HPE-supported CPE: `cpe/24.07`, `cpe/25.09` only (changelog 2026-02-13). Docs examples use `cpe/24.07`.
- Arch modules: `craype-x86-genoa` (GENOA, MI300A), `craype-x86-trento` + `craype-accel-amd-gfx90a` (MI250), `craype-accel-amd-gfx942` (MI300A). Load `amd-mixed` or `rocm` with any accelerator target.
- ROCm: default 6.4.3 with CPE 25.09. ROCm >= 7.0 available but "not compatible with the Cray-mpich versions currently deployed". Modules: `rocm`, `amd-mixed`, `PrgEnv-amd`. ROCm is backward, not forward, compatible.
- CINES software stack 5.0.0 in production (`module load develop`); 3.2.0 archived (`module load archive`).
- Python: `cray-python` (CPE) or `python` module (~100 packages). Venv recipe: `cray-python` + `virtualenv`, venv in WORK. Do not load modules after activating. `conda` module exists.
- PyTorch, documented pip wheels (`--index-url https://download.pytorch.org/whl/<rocmX.Y>`): rocm5.7; 2.4.1/rocm6.0; 2.5.0/rocm6.2 ("at least 2.5.0 is mandatory for the MI300A"); 2.6.0/rocm6.2.4; 2.9.1/rocm6.4; 2.10.0/rocm7.1. When building extensions, match `amd-mixed`/`rocm` to the torch ROCm version.
- CINES AI venv (beta): `module load develop AI-develop venv/<v>`, `AI_VENV_PATH` set before load, managed with `poverlay-pip`, create on login node. Modules listed: `venv/0.5.0+torch2.10.0+rocm6.4.0`, `venv/0.6.0+torch2.10.0` (ROCm 6.4.3), `venv/0.7.0+torch2.10.0+rocm7.2.0`, `venv/0.8.0+torch2.11.0+rocm7.2.0`. `PYTORCH_ROCM_ARCH=gfx90a;gfx942`. Older versions removed "due to the PyTorch security issue".
- Contradiction: AI venvs ship ROCm 7.2.0 while the changelog says ROCm >= 7.0 is incompatible with deployed cray-mpich. Likely irrelevant for torch-only jobs using RCCL `[UNVERIFIED]`.
- Multi-node RCCL: load `aws-ofi-rccl` (`1.18.0_rocm6` for ROCm 6.2 to <7, `1.18.0_rocm_7` for ROCm >= 7); no extra rocm module needed with PyTorch wheels. Known not to scale past 128 MI250X nodes.
- Recommended env: `MIOPEN_USER_DB_PATH=/tmp/${USER}-miopen-cache-${SLURM_JOB_ID}`, `MIOPEN_CUSTOM_CACHE_DIR=${MIOPEN_USER_DB_PATH}`, `HF_HOME=${WORKDIR}/USER_DSDIR`. FP16 denormals flushed on CDNA2: prefer BF16 or loss scaling.

Sources: `DOC/user_support/index.html` (#programming-environment), `DOC/other/changelogs.html`, `DOC/software_stack/libraries/index.html` (PyTorch, RCCL, ROCm), `DOC/software_stack/tools/index.html` (Python, Conda), `DOC/software_stack/cines_software_stack/venv_ai.html`, `DOC/quick_start/index.html`.

## 8. Policies and connection

- SSH: `ssh <login>@adastra.cines.fr`, or a given login node `adastraN.cines.fr` (recommended for VSCode).
- SSH key authentication not permitted; password only (min 12 chars, upper, lower, digit, special; expires after 1 year; change with `passwd`).
- Gateways, IP registration for SSH: not documented in pages read.
- Login nodes: for editing, compiling, submitting. No parallel programs on login nodes. No GPU on login nodes; their CPUs differ from GPU-node CPUs (no `-march=native`).
- VSCode Remote-SSH: ask svp@cines.fr for access first; set `remote.SSH.allowLocalServerDownload`.
- Graphics software: HPDA only, not on compute partitions.
- Logins are strictly personal.
- No `--qos`; no thousands of small jobs; do not over-request `--time`.
- Detailed usage rules: in the CINES user charter, not read.

Sources: `DOC/user_support/index.html` (#connecting), `DOC/architecture/index.html`, `DOC/other/faq_and_known_issues.html`, `DOC/software_stack/tools/index.html`.

## 9. Documented pitfalls

- `--threads-per-core` on `salloc`/`sbatch` breaks `srun` (1 rank, 1 core). Put it on `srun`.
- Shared mode without `--threads-per-core=1`: `--cpus-per-task=8` means 8 threads (4 cores).
- Memory request above core share is charged as cores/GPUs you cannot use.
- Shared pool can be full; exclusive may start earlier. Expect 1 to 2 h queue for a node.
- Job arrays > 11 jobs rejected.
- Wrong arch module: `Illegal instruction` (trento for MI250, genoa for GENOA).
- GCC < 13.2.0 cannot target Zen 4 (`bad value 'znver4'`).
- Slingshot 2.2.0 regression: `export FI_MR_CACHE_MONITOR=kdreg2`.
- MPICH < 8.1.28 incompatible with libfabric 2.2.0: use a `cpe` module.
- Too many processes per GPU: "Expect reduced ROCm performance".
- ROCm memory fragmentation leads to OOM.
- Store not visible from compute nodes; scratch purged after 30 days.
- Coredumps can fill the scratch quota; `ulimit -c 0` to disable.
- `cray-python` sets `PYTHONPATH`, interferes with venvs.
- Unique login: scp lands in personal home; use absolute paths.
- Conda/SVN timeouts: configure the proxy explicitly.
- Sick nodes may hang MPI collectives: report to svp@cines.fr.
- SSH idle disconnect: `ServerAliveInterval 69`.

Sources: `DOC/other/faq_and_known_issues.html`, `DOC/other/changelogs.html`, `DOC/user_support/index.html`, `DOC/data_storage_and_transfers/index.html`, `DOC/software_stack/tools/index.html`.
