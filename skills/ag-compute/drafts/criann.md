# CRIANN Austral: job reference

- Pages read: 2026-10-31. No login to any machine.
- Main source: CRIANN technical documentation at `https://services.criann.fr/services/hpc/cluster-austral/` (French). Page "last updated" stamps are given where relevant.
- Arctic = MesoNET "code-formation" subset hosted on Austral, own login `arctic.criann.fr`, own `ar_*` partitions.
- `[UNVERIFIED]` = not found in official docs read in this session, or inferred.

Base URLs used below:
- `G` = https://services.criann.fr/services/hpc/cluster-austral/guide/ (updated 2026-10-12)
- `A` = https://services.criann.fr/services/hpc/cluster-austral/architecture/ (updated 2026-04-08)
- `N` = https://services.criann.fr/services/hpc/cluster-austral/actualites/ (updated 2026-04-08)

## 1. Machines

### Hardware (from `A`)

| Node type | Count | CPU | RAM | GPU |
|---|---|---|---|---|
| Thin CPU ("fin") | 124 | 2x AMD EPYC 9654 Genoa, 96 c/socket, 2.4 GHz (192 c/node) | 768 GB DDR5-4800 (714 GB usable, see 3) | none |
| GPU A100 (hpda) | 5 | 2x AMD EPYC 7543 Milan, 32 c/socket, 2.8 GHz | 512 GB DDR4-3200 | 8x A100 80 GB HBM2e, NVLink |
| GPU A100 (general) | 6 | same as above | 512 GB | 8x A100 80 GB, NVLink |
| GPU H200 | 2 | 2x Intel Xeon 8558, 48 c/socket, 2.1 GHz | 2 TB DDR5-5600 | 8x H200 141 GB HBM3e, NVLink |
| AMD GPU ("veille techno", alt) | 2 | 1x AMD Milan 32 c | 256 GB | 4x AMD MI210 (64 GB per `G` table) |
| SMP large memory | 1 | HPE Superdome Flex 280, 8x 28 c Intel 8376H (Cooper Lake), 2.6 GHz (224 c) | 6 TB DDR4 | none |
| Visualisation | 5 | 2x EPYC 9654 | 768 GB | 2x NVIDIA L40 48 GB |
| Login | 4 | 2x EPYC 9654 | 768 GB | none |
| Transfer login | 1 | 1x AMD Rome 7313P, 16 c, 3.0 GHz | 96 GB | none |

- Interconnect: HPE Slingshot 11, 200 Gbit/s. 100 Gbit/s link to SYVIK regional network.
- Peak (from `A`): 979 TFlops CPU DP, 1195 TFlops GPU DP, 2390 TFlops GPU DP Tensor Core.
- Per-GPU FP64: not documented. Aggregate DP peak only.
- SMT enabled on NVIDIA GPU nodes: 128 logical CPUs (64 physical); AMD GPU nodes: 64 (32 physical) (`G`, "GPUs SMT").
- MIG: one A100 node split into 31 devices: 10x `a100_1g.10gb` (10 GB, 14 SM), 17x `a100_2g.20gb` (20 GB, 28 SM), 4x `a100_3g.40gb` (40 GB, 42 SM). MIG not suited for multi-GPU (`G`).

### CUDA compute capability

| GPU | CC / target | Source |
|---|---|---|
| A100 | 8.0 (`sm_80`, `craype-accel-nvidia80`, `-gpu=cc80`) | compil-gpu |
| H200 | 9.0 (`sm_90`, `craype-accel-nvidia90`, `-gpu=cc90`) | compil-gpu |
| MI210 | `gfx90a` (`craype-accel-amd-gfx90a`) | compil-gpu |

### Software base
- RHEL 9.6 (since 2026-04-07 maintenance, `N`), Slurm, Lustre, Cray PE, HPE MPI, ROCm 6.1.3 (`A`).
- NVIDIA driver: `A` says "CUDA (pilote 12.7)"; `N` (2025-11-03) says driver 580.95.05, CUDA 13.0 usable. `A` looks stale on this line.

### Discrepancies between official pages
- https://www.criann.fr/hpc-criann/index.html (read via summarising fetch) lists A100 nodes as "AMD Rome" and H200 as 140 GB; `A` says Milan 7543 and 141 GB. `A` is the technical page; prefer it.
- Austral landing page gives 24768 cores / 966 TFlops CPU; `A` gives 24960 / 979 TFlops (`A` includes later additions).

Sources: `A`; `G`; `N`; https://services.criann.fr/services/hpc/cluster-austral/guide/compil-gpu/ (updated 2026-10-14); https://services.criann.fr/services/hpc/cluster-austral/ ; https://www.criann.fr/hpc-criann/index.html

## 2. Accounts and hours

- All usage happens inside a project. Hours are allocated to the project; the project lead splits them between users (acces-calcul).
- Allocation requests through Gramc-Criann (Education-Recherche identity federation). Two calls per year: November (next year) and June (top-up). Off-cycle requests possible ("au fil de l'eau").
- User accounts: signed form + Criann charter, signed by project lead and lab director, sent to admin@criann.fr. Accounts are personal.
- Account inactive 6 months: access may be disabled (CGU).
- Annual activity report required; publications must acknowledge CRIANN ("Part of this work was performed using computing resources of CRIANN (Normandy, France)").

### Accounting rule (`G`)
- Hours = reserved cores x elapsed time, based on Slurm reservation.
- 56 cores for 3 h = 168 h. Same job with `--exclusive` on a 192-core thin node = 576 h.
- `CPUTime` = Elapsed x AllocCPUS (conso-sacct).
- GPU hour weighting: not documented.

### Commands

| Command | Use |
|---|---|
| `maconso` | own and project consumption (h.cpu), on login nodes; updated nightly; finished jobs only |
| `maconso -u` | per-account detail (project lead / deputy only) |
| `~/.acct.json` | same data in JSON |
| `sacct`, `sacct -X --start= --end=` | Slurm accounting; window = search window, not completion window |
| `sstat -j <id>` | live usage of running job |
| `.o` file | epilog appends a sacct consumption report to every job's stdout file |

### Slurm `--account`
- Not documented on any page read. The sacct example output shows an `Account` column (value `ac`). Local note "`--account=<allocation number>`, e.g. `--account=2024028`" stays `[UNVERIFIED]`.

Sources: https://www.criann.fr/acces-calcul/index.html ; https://www.criann.fr/cgu-calcul/index.html ; https://services.criann.fr/services/hpc/gramc-criann/ ; `G` ("Suivi de la consommation horaire", "Calcul de la comptabilité horaire"); https://services.criann.fr/services/hpc/cluster-austral/guide/conso-sacct/ (updated 2024-06-06)

## 3. Slurm

### Commands (`G`)
`sinfo`, `sbatch script.sl`, `squeue -u login`, `squeue --start --job <id>`, `sbatch --test-only script.sl`, `scontrol show job <id>`, `scancel <id>`.

Templates on the machine: `/soft/slurm/Modeles_scripts` (Austral), `/soft/slurm/Arctic_modeles_scripts` (Arctic). Examples: `pytorch-smt/`, `pytorch-mig/`, `exclusive_user`, `job_SMP_*.sl`.

### CPU partitions (thin Genoa nodes, 192 c, 714 GB usable)

| Partition | Max time | Nodes in partition | Max per job |
|---|---|---|---|
| debug | 30 min | 124 | 2 nodes |
| 2tcourt | 12 h | 124 | 44 nodes |
| tcourt | 24 h | 120 | 22 nodes |
| tcourt_intra | 24 h | 30 | 1 node |
| court | 48 h | 40 | 6 nodes |
| long | 100 h | 24 | 2 nodes |
| tlong | 300 h | 12 | 1 node |

- Per-user cap on parallel partitions: 4224 cores (22 nodes) weekdays, 8448 cores (44 nodes) weekend (Fri 17:00 to Sun 20:00).

### GPU and special partitions

| Partition | Max time | Nodes | Max per job |
|---|---|---|---|
| gpu | 24 h | 6 Milan + 8x A100 80 GB | 2 nodes (16 GPU, 256 c, 2x480000 MB) |
| hpda | 48 h | 4 Milan + 8x A100 80 GB | 1 node (8 GPU, 128 c, 480000 MB) |
| gpu_all | 24 h | gpu + hpda nodes | 1 node (8 GPU, 128 c, 480000 MB) |
| hpda_mig | 24 h | 1 MIG A100 node | see MIG |
| gpu_debug | 30 min | gpu + hpda nodes | 1 GPU, 16 c; 1 running job; higher priority |
| gpu_h200 | 24 h | 2 Xeon + 8x H200 141 GB | half node (4 GPU, 96 c) |
| amdgpu | 72 h | 2 Milan + 4x MI210 64 GB | 2 nodes (8 GPU, 64 c, 2x242000 MB) |
| smplarge | 3 h | SMP node | 1 node (224 c, 6092000 MB) |
| smplong | 72 h | SMP node | half node (112 c, 3046000 MB) |

- Per-user GPU caps, gpu + gpu_all + hpda: 16 GPU / 128 c weekdays, 32 GPU / 256 c weekend.
- gpu_h200: 4 GPU / 96 c weekdays, 8 GPU / 192 c weekend.
- Note: `G` says hpda has 4 nodes, `A` says 5 hpda nodes; one is the MIG node (hpda_mig).

### Arctic partitions (MesoNET users, `arctic.criann.fr`)

| Partition | Max time | Max per job |
|---|---|---|
| ar_mig | 8 h | 4 c, 1 MIG instance |
| ar_a100 | 8 h | 16 c, 1 A100 |
| ar_h200 | 8 h | 24 c, 1 H200 |
| ar_mi210 | 8 h (`G`) / 1 h (MesoNET doc) | 16 c, 1 MI210 |
| ar_fin | 3 h | 384 c (2 Genoa nodes) |

### GPU request syntax
- Full GPUs: `--gpus=X`, or `--gpus-per-node=`, `--gpus-per-task=` (ia-deep-learning page; it writes them with a single dash, a typo).
- MIG: `--partition hpda_mig --gres=gpu:a100_1g.10gb` (or `a100_2g.20gb`, `a100_3g.40gb`).
- NVIDIA GPU jobs must run on gpu, hpda, gpu_all, gpu_debug, hpda_mig or gpu_h200.
- Recommended `--cpus-per-task` per GPU: 16 (gpu, hpda, gpu_all, gpu_debug), 4 (hpda_mig), 24 (gpu_h200).
- MPI multi-GPU with 1 rank per GPU: add `#SBATCH --hint nomultithread`.
- GPU-aware MPI (Cray MPICH): `export MPICH_GPU_SUPPORT_ENABLED=1`.

### Memory rules
- Thin node: max `--mem 714gb` or `--mem 732000` per node (`G`). News 2024-02-22: 714000M total, 3500M per core.
- NVIDIA GPU nodes: 480000 MB per node in `G` table; news 2024-02-22 said 492000M (7600M/core). Use `G`.
- Default memory per core on gpu, hpda, gpu_all, gpu_debug: 3750 MB (news 2025-04-11). hpda_mig default 4 cores per GPU.
- Default memory per core on CPU partitions: not documented.

### Mandatory options
- Partition must be set by the user (stated on Arctic jobs page). For Austral, every example sets `-p`. Default partition: not documented.
- Time: examples set `-t`. Default time limit: not documented.
- Multi-node MPI: add `--exclusive` (news 2024-02-22). `--exclusive=user` lets one user's jobs share a node.
- `--account`: not documented, see 2.

### Signals and end of job
- At time limit: SIGTERM, about 30 s, then SIGKILL.
- `#SBATCH --signal=B:SIGUSR1@120` sends SIGUSR1 120 s before the limit to the batch script; trap it, run `srun ... &` then `wait`.
- `scancel` sends SIGCONT, SIGTERM, then SIGKILL about 30 s later.
- Output: `.o` and `.e` files; docs advise reading the `.e`.

### Example scripts
Only the signal example below is copied from the docs. The other three are composed from documented options and are `[UNVERIFIED]` as complete scripts (`--account` line in particular). Check `/soft/slurm/Modeles_scripts` on the machine.

Documented (signals page, abridged):
```bash
#!/bin/bash
#SBATCH --mem-per-cpu=3000
#SBATCH -n 1
#SBATCH -t 0:5:00
#SBATCH -p debug
#SBATCH --signal=B:SIGUSR1@120
trap 'echo trapped; exit 2' SIGUSR1
cd $LOCAL_WORK_DIR
srun ./code.exe &
wait
```

CPU, 1 thin node MPI `[UNVERIFIED]`:
```bash
#!/bin/bash
#SBATCH -J cpu_job
#SBATCH -p court
#SBATCH -N 1
#SBATCH -n 192
#SBATCH --exclusive
#SBATCH --mem 714gb
#SBATCH -t 24:00:00
#SBATCH --account=<project_id>    # [UNVERIFIED]
#SBATCH -o %x.%j.o
#SBATCH -e %x.%j.e
module purge; module load <modules>
srun ./app
```

1 A100 `[UNVERIFIED]`:
```bash
#!/bin/bash
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=16
#SBATCH -t 12:00:00
#SBATCH --account=<project_id>    # [UNVERIFIED]
module purge
module load aidl/pytorch/2.6.0-cuda12.6
srun python train.py
```

Multi-GPU, 8 A100 on one node `[UNVERIFIED]`:
```bash
#!/bin/bash
#SBATCH -p gpu
#SBATCH -N 1
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=16
#SBATCH -t 24:00:00
#SBATCH --account=<project_id>    # [UNVERIFIED]
module purge
module load aidl/pytorch/2.6.0-cuda12.6
srun python train_ddp.py
```
For 2 nodes (16 GPU) use `-N 2` on `gpu` only (gpu_all and hpda are 1 node max).

Sources: `G` ("Environnement de soumission", "GPUs SMT", "GPUs MIG", "Usage exclusif"); `N` (2024-02-22, 2025-04-11); https://services.criann.fr/services/hpc/cluster-austral/guide/ia-deep-learning/ (updated 2025-05-26); https://services.criann.fr/services/hpc/cluster-austral/guide/signals-sent-by-slurm/ ; https://services.criann.fr/services/hpc/cluster-austral/guide/compil-gpu/ ; https://www.mesonet.fr/documentation/user-documentation/code_form/arctic/jobs

## 4. Storage

Single Lustre filesystem, 1 PB flash pool + 1 PB disk pool, visible on all cluster nodes. Flash is default; when flash fills, large files are migrated to disk automatically.

| Path | Role | Quota |
|---|---|---|
| `/home/<project_id>/<login>` | home | 50 GB hard |
| `/home/<project_id>/PARTAGE` | project shared space | 200 GB hard |
| `/dlocal/run/<jobid>` | per-job scratch | user totals only |
| `/dlocal/home/<project_id>` | permanent compute space, on qualified need | informative, no limit |
| `/soft` | CRIANN software | n/a |
| per user, whole array | | 30 TB hard (protection), 5 M inodes hard |

- No backup of user data.
- Quota is 50 GB per user home directory, not per allocation (local note said "per allocation": wrong per docs). Quotas raisable on justified request to support@criann.fr.
- `cri_quota` shows usage; `lfs quota` also works.
- Scratch purge: `/dlocal/run/<jobid>` deleted N days after job end. N is inconsistent across official pages: 30 days (data-management, updated 2026-08-04), 45 days (news 2025-06-02), 60 days (news 2024-06-07). Treat as 30 days.
- `$LOCAL_WORK_DIR` = `/dlocal/run/<jobid>`: used in Austral signal example; the definition is stated only in the MesoNET Boreale guide on the same site. For Austral `[UNVERIFIED]` but consistent.
- Pool control: `lfs setstripe --pool disk <dir>`, `lfs migrate --pool flash <file>`, `lfs getstripe --pool <file>`. `mv` keeps the original pool; use `cp` to change it.
- Visibility on compute nodes: same Lustre tree on all nodes (data-management). Node-local disks: not documented.

Sources: https://services.criann.fr/services/hpc/cluster-austral/guide/data-management/ (updated 2026-08-04); `N`; https://services.criann.fr/services/hpc/mesonet-project/guide/ ; https://www.criann.fr/cgu-calcul/index.html

## 5. Network and access

| Host | Use |
|---|---|
| `austral.criann.fr` | login (front1-3, 195.221.22.130-132) |
| `arctic.criann.fr` | Arctic login (front4, 195.221.22.133) |
| `austral-transfert.criann.fr` | external data transfer (195.221.22.134) |
| `https://austral-hub.criann.fr` | JupyterHub (Austral OpenID, same login/password) |

- SSH port 22. If the home site filters outbound traffic, open all five IPs (services can move between hosts during maintenance).
- IP filtering on CRIANN side, gateway, VPN: not documented.
- First login: forced password change, session then closes; reconnect.
- SSH key recommended (`ssh-copy-id login@austral.criann.fr`); password still needed for JupyterHub and visualisation. Private key must never be copied to a server.
- SSH tunnelling to the login nodes is forbidden; VS Code "Remote SSH" does not work. Suggested alternatives: git, vscode-rsync plugin, JupyterHub, sshfs (CT HPC 2024-04-09 slides).
- Internet access from login nodes: not documented. git client is installed on login nodes.
- Internet access from compute nodes: not documented.
- Remote visualisation: `startvisu` on a login node, then TurboVNC client.

Sources: `G` ("Se connecter sur Austral", "Firewall"); https://services.criann.fr/services/hpc/cluster-austral/guide/security/ (updated 2026-04-23); https://services.criann.fr/services/hpc/cluster-austral/guide/jupyter/ ; https://services.criann.fr/services/hpc/cluster-austral/guide/visu/ ; https://www.criann.fr/docs/0/actus/2024/CT-HPC-20240409.pdf (slide 23)

## 6. Containers

- Apptainer / Singularity: not documented anywhere in the Austral guide, news, Arctic pages or CT HPC slides read (2024-04, 2024-06, 2024-10, 2025-04). No mention of `--nv` or image rules.
- Local note "apptainer available on compute nodes only" stays `[UNVERIFIED]`. Check with `module avail`, `which apptainer` in a job, or ask support@criann.fr.
- Related documented tool: `squashfuse` / `fusermount -u` work in user space for mounting SquashFS dataset archives (ia-deep-learning).

Sources: all Austral pages listed in this file (grep for apptainer/singularity/conteneur/container: no hit); https://www.mesonet.fr/documentation/user-documentation/code_form/arctic/logiciels

## 7. Software

- Environment modules: `module avail|load|unload|list|purge|help`.
- Module names by category: `aidl/` (AI), `atomic_simu/`, `bio`, `cfd_fem/`, `math`, `climate`, `data`, `mesh`, `couplers`, `py_env`, `cpe_env`, `tools/`. Search by app name also works (`module avail python`, `module avail anaconda`).
- Compilers: Cray PE wrappers `cc`/`CC`/`ftn` replace gcc/icc/mpicc etc. Default module `cpe_env/gcc13.2.1-mpich8.1.30-milan-02.25`. Genoa-optimised alternatives exist.
- GPU code must be compiled on compute nodes (login nodes lack the libraries / OS of some nodes). Run `module purge` before submitting the build job (gpu_all or gpu_h200).
- Python and AI: PyTorch and TensorFlow under python3 module environments.

| Module | Python | CUDA | torch |
|---|---|---|---|
| aidl/pytorch/2.2.0-cuda12.1 | 3.12.2 | 12.1 | 2.2.0 |
| aidl/pytorch/2.4.1-cuda12.1 | 3.12.3 | 12.1 | 2.4.1 |
| aidl/pytorch/2.5.1-cuda12.4 | 3.12.3 | 12.4 | 2.5.1 |
| aidl/pytorch/2.6.0-cuda12.6 | 3.13.2 | 12.6 | 2.6.0 |
| aidl/tensorflow/2.16.1-cuda12 | 3.9.18 | 12.3 | TF 2.16.1 |

(older 1.11.0, 2.0.0, TF 2.11.0 also listed.)
- H200 nodes: only `aidl/pytorch/2.6.0*` works.
- Missing packages: ask support-calcul@criann.fr, or `pip install --user <pkg>` (installs to a per-module dir, e.g. `~/.python3-3.10-torch200/site-packages`).
- conda, uv, venv guidance: not documented beyond `module avail anaconda`.

Sources: https://services.criann.fr/services/hpc/cluster-austral/guide/modules/ ; `G` ("Compilation", "Logiciels disponibles"); https://services.criann.fr/services/hpc/cluster-austral/guide/ia-deep-learning/ ; https://services.criann.fr/services/hpc/cluster-austral/guide/compil-gpu/

## 8. Policies

- Login nodes: interactive use limited to compiling, editing, submitting, small and short tests.
- Interruption of multi-threaded processes on login nodes: not documented (local note `[UNVERIFIED]`).
- No admin commands (`sudo`, `apt-get`, `yum` reserved to CRIANN). Software installed by CRIANN on request.
- Accounts strictly personal: no password sharing, no adding someone else's SSH key.
- Users must follow the tech docs and news; maintenance announced by mailing list and login-node messages. All connections are logged.
- JupyterHub: 1 jupyterlab per login; partitions tcourt_intra, hpda, hpda_mig only; lifetime 8 h (same page also says Slurm stops it at 12 h: inconsistent).

Sources: https://services.criann.fr/services/hpc/cluster-austral/ ; https://www.criann.fr/cgu-calcul/index.html ; https://www.criann.fr/docs/0/actus/2024/CT-HPC-20240409.pdf (slide 24) ; https://services.criann.fr/services/hpc/cluster-austral/guide/jupyter/

## 9. Pitfalls stated by the docs

- Lustre handles many small files badly: inode quota 5 M, slow training. Pack datasets (SquashFS + squashfuse, WebDataset tar, HDF5).
- `mv` does not change Lustre pool; files may silently move flash to disk when flash fills.
- Do not modify a file during `lfs migrate`.
- Scratch `/dlocal/run/<jobid>` is purged after job end; nothing is backed up anywhere.
- `--exclusive` on a thin node bills all 192 cores.
- SMT on GPU nodes: CPU counts are logical. Use `--hint nomultithread` for 1-rank-per-GPU MPI.
- MIG devices not for multi-GPU.
- H200: only PyTorch 2.6.0 module works.
- GPU code: compile on compute nodes, not login nodes.
- Makefiles must use `cc`/`CC`/`ftn` (except HPE MPI on SMP node).
- At time limit only ~30 s between SIGTERM and SIGKILL; use `--signal` for checkpointing.
- Read the `.e` file after each job.
- OpenFOAM: use collated file handler to avoid file explosion.
- Partition limits changed several times (2024-2025); check `sinfo` and the news page before relying on this file.

Sources: https://services.criann.fr/services/hpc/cluster-austral/guide/data-management/ ; https://services.criann.fr/services/hpc/cluster-austral/guide/ia-deep-learning/ ; `G` ; `N` ; https://services.criann.fr/services/hpc/cluster-austral/guide/signals-sent-by-slurm/

## Not found / to ask support (support@criann.fr)
- `--account` syntax and whether it is required.
- Apptainer/Singularity availability, `--nv`, image location rules.
- Internet from login and compute nodes; proxy.
- Login-node CPU/thread limits.
- GPU-hour billing weight; default partition, time and CPU-partition memory.
- Per-GPU FP64 figures.

## Pages inaccessible
- https://www.criann.fr/support.html redirects (301) to http://www-tech.criann.fr/ ; not followed.
- https://www.mesonet.fr/documentation/user-documentation/ is a Docusaurus site; Arctic pages read via sitemap URLs.
