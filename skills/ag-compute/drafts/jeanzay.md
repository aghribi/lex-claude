# Jean Zay (IDRIS) job reference

- Pages read: 2026-10-31, with `curl` from `http://www.idris.fr/docs/...` (French). The English mirror lives at `http://www.idris.fr/en/docs/...`. One page was spot-checked against it and matched.
- The IDRIS site was redesigned in 2026 (Flash Info 2026-04). The old URLs `http://www.idris.fr/jean-zay/` and `http://www.idris.fr/eng/jean-zay/` return HTTP 404. Links inside blog posts that point to `.../jean-zay/gpu/*.html` are dead.
- Every fact below comes from a page read on that date. `[UNVERIFIED]` means not taken from IDRIS docs. "Doc inconsistency" means two IDRIS pages disagree.
- No machine was logged in to.

## 1. Machines

OS: RedHat 9.6 (since 2026-02-17). Slurm 23.11.3 (since 2024-10-01). Filesystem: Lustre. Interconnect: Omni-Path (HPE SGI 8600 part), InfiniBand (Bull XH3000 / H100 part).

| Partition | Selector | Nodes | CPU per node | Cores/node | RAM/node (usable) | GPUs/node | GPU | GPU mem | Cores per GPU (doc ratio) |
|---|---|---|---|---|---|---|---|---|---|
| cpu_p1 | default for CPU jobs | 720 | 2x Intel Xeon Gold 6248 (20c, 2.5 GHz) | 40 | 192 GB (156 GB) | - | - | - | - |
| gpu_p13 | default for GPU jobs; `-C v100-16g` / `-C v100-32g` | 396 (126 x 16 GB, 270 x 32 GB) | 2x Xeon Gold 6248 | 40 | 192 GB (156 GB) | 4 | V100 SXM2 | 16 or 32 GB | 10 |
| gpu_p2 / gpu_p2s / gpu_p2l | `--partition=gpu_p2[s|l]` | 31 (20 x 384 GB, 11 x 768 GB) | 2x Xeon Gold 6226 (12c, 2.7 GHz) | 24 | 384 / 768 GB (360 / 720 GB) | 8 | V100 SXM2 | 32 GB | 3 |
| gpu_p5 (A100) | `-C a100` | 52 | 2x AMD EPYC 7543 Milan (32c, 2.8 GHz) | 64 | 512 GB (468 GB) | 8 | A100 SXM4, NVLink | 80 GB | 8 |
| gpu_p6 (H100) | `-C h100` | 364 | 2x Intel Xeon Platinum 8468 (48c, 2.1 GHz) | 96 | 512 GB (468 GB) | 4 | H100 SXM5, NVLink | 80 GB | 24 |
| prepost | `--partition=prepost` | 4 | 4x Intel Skylake 6132 (12c, 3.2 GHz) | 48 | 3 TB (2.88 TB) | 1 | V100 | not stated | - |
| visu | `--partition=visu` | 5 | 2x Intel Cascade Lake 6248 (20c) | 40 | 192 GB | 1 | Quadro P6000 | not stated | - |
| compil | `--partition=compil` | 3 compile nodes + the 4 prepost nodes | 1x Xeon Silver 4114 (10c, 2.2 GHz) | 10 | 96 GB | - | - | - | - |
| compil_h100 | `--partition=compil_h100` | 1 | 2x Xeon Platinum 8468 (same CPUs as gpu_p6) | 96 | 256 GB | - | - | - | - |
| archive | `--partition=archive` | same nodes as prepost | - | - | - | - | - | - | - |
| login | `ssh jean-zay.idris.fr` | 5 | 2x Cascade Lake 6248 | 40 | 192 GB | none | - | - | - |

- prepost nodes also have a 1.5 TB internal NVMe disk.
- CUDA compute capability: **not documented** by IDRIS. `[UNVERIFIED]`, from NVIDIA's general specs recalled from memory: V100 = 7.0, A100 = 8.0, H100 = 9.0.
- CUDA modules older than `cuda/12.0.0` do not work on gpu_p6 (H100).
- Doc inconsistencies:
  - The hardware page gives the prepost CPU as "4x Skylake 6132". The SSH page says "dual-socket Cascade Lake 6132, 12 cores".
  - Usable RAM per gpu_p2s node is 360 GB on the partitions page, but 320 GB in the memory formula on the memory-allocation page.

Sources:
- http://www.idris.fr/docs/jean-zay/jean-zay/jean-zay-hardware
- http://www.idris.fr/docs/jean-zay/slurm/slurm_partitions_gpu
- http://www.idris.fr/docs/jean-zay/slurm/slurm_partitions_cpu
- http://www.idris.fr/docs/jean-zay/slurm/exec_alloc-mem
- http://www.idris.fr/docs/jean-zay/logiciels_bibliotheques/logiciels_hpc/cudatoolkit
- http://www.idris.fr/docs/jean-zay/gestion-compte/connexion-ssh

## 2. Accounts and hours

- Hours are allocated per project. CPU hours and GPU hours are counted separately, and GPU hours are split by type: V100, A100, H100.
- `--account` is required in these cases:
  - the login belongs to several projects;
  - one project has both CPU and GPU hours;
  - one project has more than one GPU type.

  Without it, hours may be charged to the wrong project.
- Syntax: `--account=<proj>@cpu`, `@v100`, `@a100` or `@h100`. The suffix must match the partition and QoS used.
- `$IDRPROJ` holds the active project. `idrproj` lists all projects for the login.
- Normalised GPU hours (for the access type threshold): 50k V100 h = 25k A100 h = 12.5k H100 h.
  - Regular access (AR): at least 500k CPU h or at least 50k normalised GPU h.
  - Dynamic access (AD): below those thresholds.

Accounting:

| Job type | Charged |
|---|---|
| CPU | physical cores reserved x elapsed time |
| GPU | GPUs reserved x elapsed time. "Reserved" is raised to match the CPU share requested. |
| Multi-node (any job asking more than 1 node) | always exclusive: whole nodes are charged, including partly used ones |

- Example from the doc: `--gres=gpu:1` with half of the node's CPUs is billed as half the node's GPUs (2 on a 4-GPU node, 4 on an 8-GPU node).
- Another doc example: `--ntasks=1 --gres=gpu:1 --cpus-per-task=20` on gpu_p13 is billed as 2 GPUs.
- Whole-node cost in exclusive mode:
  - CPU: 40 cores.
  - gpu_p13: 4 GPUs.
  - gpu_p2: 8 GPUs.
  - gpu_p5: 8 GPUs.
  - gpu_p6: not listed on the hours page. By the node layout it would be 4 GPUs. `[UNVERIFIED]`
- Example: 5 GPUs on gpu_p13 is billed as 8 GPUs (2 nodes).
- prepost, visu, compil and archive are not billed. They are usable even without CPU hours.
- `idracct` shows allocation and per-member use for each project.
  - `-a CPU|V100|A100|H100` filters by hour type (uppercase).
  - `-s` prints a summary.
- Regulation:
  - The initial allocation is automatically raised by 25 %. Hours beyond the initial allocation run at low priority.
  - The project is blocked once the effective allocation is used up.
  - Fairshare uses past consumption with a 14-day half-life.
  - Since 2025-09-16, the global AR/AD split (70/30) also feeds priority.
  - `idr_compuse` shows whether a project is under- or over-consuming.
- Refunds: possible if lost hours exceed 5 % of the allocation (open a ticket). The 125 % headroom is meant to absorb small losses.

Sources:
- http://www.idris.fr/docs/jean-zay/gestion-compte/heures-calcul
- http://www.idris.fr/docs/jean-zay/gestion-compte/heures-calcul-regulation
- http://www.idris.fr/docs/jean-zay/nouvel-utilisateur
- http://www.idris.fr/docs/faq/faq

## 3. Slurm

### Required or expected options

| Partition | Required | CPU per GPU (`--cpus-per-task` at 1 task per GPU) | Modules |
|---|---|---|---|
| cpu_p1 | nothing (default) | - | default |
| gpu_p13 | `--gres=gpu:N` (max 4) | 10 | default |
| gpu_p2 | `--partition=gpu_p2` (or `gpu_p2s` / `gpu_p2l`), `--gres=gpu:N` (max 8) | 3 | default |
| gpu_p5 A100 | `-C a100` (or `--constraint=a100`), `--gres=gpu:N` (max 8) | 8 | `module load arch/a100` before any other module |
| gpu_p6 H100 | `-C h100`, `--gres=gpu:N` (max 4) | 24 | `module load arch/h100` before any other module |
| prepost / visu / compil / archive | `--partition=<name>` | - | - |

- `--hint=nomultithread` appears in every IDRIS example and reserves physical cores. The docs recommend it but do not call it mandatory.
- A100 and H100 codes must be recompiled with the `arch/*` modules. Default modules target CPU and V100 nodes.

### Time limits per partition

| Partition | Default | Max |
|---|---|---|
| cpu_p1 | 10 min | 100 h |
| gpu_p13, gpu_p2 | 10 min | 100 h |
| gpu_p5 (A100) | 10 min | 20 h |
| gpu_p6 (H100) | 10 min | 100 h |
| prepost | 2 h | 20 h |
| visu | 10 min | 4 h |
| archive, compil, compil_h100 | 2 h | 20 h |

The default limits are deliberately low. Always set `--time`.

### QoS

Set with `--qos=<name>`. QoS names differ per partition. Service partitions have no QoS.

| QoS | Max time | Per job | Per user | Per project | Whole QoS |
|---|---|---|---|---|---|
| qos_cpu-t3 (default) | 20 h | 10240 cores (256 nodes) | 20480 cores | 20480 cores | - |
| qos_cpu-t4 | 100 h | 160 cores (4 nodes) | 640 cores | 640 cores | 5120 cores |
| qos_cpu-dev | 2 h | 5120 cores (128 nodes) | 5120 cores, 10 jobs max | 5120 cores | 10240 cores |
| qos_gpu-t3 (V100 default) | 20 h | 640 GPU | 640 GPU | 640 GPU | - |
| qos_gpu-t4 (V100) | 100 h | 16 GPU | 96 GPU | 96 GPU | 256 GPU |
| qos_gpu-dev (V100) | 2 h | 32 GPU | 32 GPU, 10 jobs max | 32 GPU | 512 GPU |
| qos_gpu_a100-t3 (A100 default) | 20 h | 128 GPU | 256 GPU | 256 GPU | - |
| qos_gpu_a100-dev | 2 h | 32 GPU | 32 GPU, 10 jobs max | 32 GPU | 128 GPU |
| qos_gpu_h100-t3 (H100 default) | 20 h | 512 GPU | 512 GPU | 512 GPU | - |
| qos_gpu_h100-t4 | 100 h | 16 GPU | 64 GPU | 64 GPU | 192 GPU |
| qos_gpu_h100-dev | 2 h | 32 GPU | 32 GPU, 10 jobs max | 32 GPU | 384 GPU |

- A100 has no t4 QoS. The A100 QoS names changed on 2024-10-01: `qos_gpu-t3` and `qos_gpu-dev` no longer apply to A100.
- Priority order: dev > t3 > t4. Waiting time in the queue raises priority.
- Doc inconsistency: the FAQ says all qos_gpu-t4 jobs together are capped at "32 converged nodes". The partitions page says 256 GPUs, which is 64 four-GPU nodes.

### Memory

- `--mem`, `--mem-per-cpu` and `--mem-per-gpu` are **disabled**.
- Memory is proportional to the cores reserved. Adjust it with `--cpus-per-task`.

| Partition | Memory per reserved core (nomultithread) | Memory per GPU at the doc ratio |
|---|---|---|
| cpu_p1 | 3.9 GB | - |
| prepost | 60 GB | - |
| gpu_p13 | 3.9 GB | 39 GB (10 cores) |
| gpu_p2s / gpu_p2l | 15 / 30 GB | 45 / 90 GB (3 cores) |
| gpu_p5 | 7.3 GB | 58 GB (8 cores) |
| gpu_p6 | 4.87 GB | 117 GB (24 cores) |

- Halve these values without `--hint=nomultithread`.
- Asking for more cores to get more memory raises the bill (more GPUs charged).
- `scontrol show job $JOBID` shows the memory. While the job is PENDING, the value may show half the real amount with nomultithread.

### Job arrays

- `#SBATCH --array=0-N`, `0-N:STEP`, `1,3,8`, `0-19%5` (`%` caps concurrent tasks).
- Allowed **only via `sbatch`**.
- Variables: `SLURM_ARRAY_JOB_ID`, `SLURM_ARRAY_TASK_ID`, `SLURM_ARRAY_TASK_COUNT`, `_MIN`, `_MAX`.
- Output name patterns: `%A` (array job ID), `%a` (task ID). Default output file: `slurm-%A_%a.out`.
- Max array size: not documented.

### Interactive

- Shell on a CPU node: `srun --pty --ntasks=1 --cpus-per-task=4 --hint=nomultithread [opts] bash`
- Shell on a GPU node: `srun --pty --nodes=1 --ntasks-per-node=1 --cpus-per-task=10 --gres=gpu:1 --hint=nomultithread [opts] bash`. Adapt `-C` and cores per GPU to the partition.
- Reusable allocation:
  - `salloc ...`, then `srun ./code` for each run.
  - After `salloc` the shell is still on the login node. `srun` is required to use the allocation.
  - `exit` releases it. Otherwise hours run until `--time`.
- MPI is not usable in the GPU `--pty` configuration.
- `ssh <node>` works only from `jean-zay` or `jean-zay-pp`, and only to nodes running one of your jobs (pam_slurm_adopt).

### Other

- `module purge` in the script is required: modules loaded at `sbatch` time are inherited.
- After hardware incidents, jobs are requeued automatically. Use `--no-requeue` if the code has no restart.
- Chained jobs: `sbatch --dependency=afterok:$JID ...`. Add `--kill-on-invalid-dep=yes` to avoid jobs stuck in `DependencyNeverSatisfied`.
- Use `srun`, not `mpirun`.
- Call `squeue` no more than 1 to 2 times per minute from scripts.
- `squeue --start` gives an estimated start time.

### Example scripts

CPU (doc, `exec_batch`):

```bash
#!/bin/bash
#SBATCH --job-name=Seq
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --hint=nomultithread
#SBATCH --time=00:01:00
#SBATCH --output=Seq%j.out
#SBATCH --error=Seq%j.out
##SBATCH --account=<proj>@cpu         # required if multi-project or several hour types
cd ${SLURM_SUBMIT_DIR}
module purge
module load ...
set -x
./seq.exe
```

1 GPU, H100 (doc, `exec_batch`; account line from the H100 blog example):

```bash
#!/bin/bash
#SBATCH --job-name=mono_gpu
#SBATCH -C h100
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=24           # 1/4 of the node's 96 cores
#SBATCH --hint=nomultithread
#SBATCH --time=00:10:00
#SBATCH --output=mono_gpu%j.out
#SBATCH --error=mono_gpu%j.out
#SBATCH --account=<proj>@h100
module purge
module load arch/h100
module load ...
set -x
python -u script_mono_gpu.py
```

1 GPU on A100: same as above with `-C a100`, `--cpus-per-task=8`, `module load arch/a100`, `--account=<proj>@a100`. Max 8 GPUs per node.

Multi-GPU, 2 A100 nodes (doc, `nouvel-utilisateur`):

```bash
#!/bin/bash
#SBATCH --job-name=TravailGPU
#SBATCH --output=TravailGPU%j.out
#SBATCH --error=TravailGPU%j.err
#SBATCH --constraint=a100
#SBATCH --nodes=2
#SBATCH --ntasks=16                  # 1 task per GPU
#SBATCH --gres=gpu:8                 # per node
#SBATCH --cpus-per-task=8
#SBATCH --time=20:00:00
##SBATCH --qos=qos_gpu_a100-t3       # default
#SBATCH --hint=nomultithread
#SBATCH --account=<proj>@a100
module purge
conda deactivate
module load arch/a100
module load pytorch-gpu/py3/2.3.0
set -x
srun python script.py
```

Multi-GPU, N H100 nodes. IDRIS documents no multi-node H100 script. This one is assembled from documented values: the A100 DDP pattern, 4 GPUs and 24 cores per GPU on H100, `-C h100`, `arch/h100`. `[UNVERIFIED as a whole]`

```bash
#!/bin/bash
#SBATCH --job-name=torch-multi-gpu
#SBATCH -C h100
#SBATCH --nodes=N
#SBATCH --ntasks-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=24
#SBATCH --hint=nomultithread
#SBATCH --time=20:00:00
#SBATCH --output=torch-multi-gpu%j.out
#SBATCH --account=<proj>@h100
module purge
module load arch/h100
module load pytorch-gpu/py3/<version>
srun python myscript.py
```

- The IDRIS blog shows a single-node H100 job with 3 tasks, `--gres=gpu:3` and `--cpus-per-task=24`.
- For DDP, the `idr_torch` module (shipped in the IDRIS PyTorch modules) sets `MASTER_ADDR` / `MASTER_PORT`. It exposes `rank`, `local_rank`, `size` and `cpus_per_task`.

Sources:
- http://www.idris.fr/docs/jean-zay/slurm/slurm_partitions_gpu
- http://www.idris.fr/docs/jean-zay/slurm/slurm_partitions_cpu
- http://www.idris.fr/docs/jean-zay/prepost/slurm-prepost-visu-archive-compil
- http://www.idris.fr/docs/jean-zay/slurm/exec_alloc-mem
- http://www.idris.fr/docs/jean-zay/slurm/exec_batch
- http://www.idris.fr/docs/jean-zay/slurm/exec_interactif
- http://www.idris.fr/docs/jean-zay/slurm/exec_jobarray
- http://www.idris.fr/docs/jean-zay/slurm/exec_multi-etapes
- http://www.idris.fr/docs/jean-zay/slurm/slurm
- http://www.idris.fr/docs/jean-zay/nouvel-utilisateur
- http://www.idris.fr/docs/jean-zay/intelligence_artificielle/distribution_parallelisme/data-parallelism-pytorch
- http://www.idris.fr/blog/impacts-extension-h100-jean-zay
- http://www.idris.fr/blog/flash-info-2026-04
- http://www.idris.fr/docs/faq/faq

## 4. Storage

| Space | Variable | Quota | Backup | Purge | On compute nodes | Use |
|---|---|---|---|---|---|---|
| HOME | `$HOME` | 3 GB, 150k inodes per user | yes | no | yes | config, small files |
| WORK | `$WORK`, shared part `$ALL_CCFRWORK` | 5 TB, 500k inodes per project (raisable) | **no** | no | yes | sources, inputs/outputs; about 300 GB/s |
| SCRATCH | `$SCRATCH`, `$ALL_CCFRSCRATCH` | "very large safety quotas": about 1/10 of the space, about 150M inodes per project; 4.6 PB shared | no | files not read or modified for **30 days** are deleted | yes | large I/O; SSD, over 1 TB/s |
| JOBSCRATCH | `$JOBSCRATCH` | as SCRATCH | no | deleted at job end | yes | per-job temporary. Visible from login at `/lustre/fsn1/jobscratch/${LOGNAME}_${JOBID}` |
| STORE | `$STORE`, `$ALL_CCFRSTORE` | 50 TB, 100k inodes per project (raisable) | no | no | **no**: login, prepost, archive, compil and visu only (since 2024-07-22) | long-term archives. Max 10 TiB per file, min 250 MiB per file recommended. Tape-backed. |
| DSDIR | `$DSDIR` | 3.3 PB total | - | - | read-only | public datasets and models, e.g. `$DSDIR/HuggingFace/`. Request additions at assist@idris.fr. |

- `CCFR`-prefixed aliases exist: `$CCFRHOME`, `$CCFRWORK`, `$CCFRSCRATCH`, `$CCFRSTORE`.
- Multi-project logins get one WORK, SCRATCH and STORE per project. `idrenv` lists all the variables.
- `idr_quota_user` (personal view, HOME plus active project) and `idr_quota_project` (per member).
  - Options: `--project <p>`, `--all-projects`, `--space home work`, `--order storage`.
  - Data is refreshed once a night, so it is not real time.
  - Real time: `du -hd0 dir`, `du -hd0 --inodes dir`.
  - `idrquota` no longer exists.
- When a quota is hit:
  - No email is sent.
  - Writes fail with `Disk quota exceeded`, and running jobs can break.
  - Editing a file at the quota limit can truncate it to zero.
- Move STORE data in and out with chained jobs on `--partition=archive` or `prepost`.
- Keep directories to a few tens of thousands of entries at most (Flash Info 2026-04).

Sources:
- http://www.idris.fr/docs/jean-zay/environnement/espaces-disques
- http://www.idris.fr/docs/jean-zay/environnement/espaces-disques-quota
- http://www.idris.fr/docs/jean-zay/environnement/gpu-dataset
- http://www.idris.fr/docs/jean-zay/slurm/exec_multi-etapes
- http://www.idris.fr/blog/impacts-extension-h100-jean-zay
- http://www.idris.fr/blog/flash-info-2026-04

## 5. Network

| Where | Internet |
|---|---|
| Login nodes (`jean-zay`) | HTTP/HTTPS proxy (`git`, `wget` work) |
| Compute nodes | **none**. No git, pip or conda downloads. |
| prepost nodes | The docs say downloads must be done "from the login nodes or the pre/post-processing nodes". The mechanism (proxy or not) is not documented. |

- Git over HTTPS is recommended (a token may be needed, e.g. GitHub).
  - Outbound SSH to a git server requires declaring its IP on the FGC form ("outgoing flows" table).
  - SSH is refused when HTTPS is available, e.g. github.com and gitlab.com.
- The IDRIS machine and service IP range is 130.84.132.0/23. JupyterHub is at 130.84.132.56.

Sources:
- http://www.idris.fr/docs/jean-zay/nouvel-utilisateur
- http://www.idris.fr/docs/faq/faq
- http://www.idris.fr/blog/impacts-extension-h100-jean-zay

## 6. Containers

- The runtime is **Singularity**: `module load singularity`, `module show singularity`.
  - Apptainer is not mentioned in the docs read.
  - Docker and Podman are not available. Docker images can be used through Singularity.
- `$SINGULARITY_CACHEDIR` is created automatically in `$SCRATCH`. The docs advise not changing it.
- Run Singularity commands from `$WORK` or `$SCRATCH`.
- Login nodes are limited to 5 GB RAM per user. Use prepost nodes for heavy builds or conversions.
- Building:
  - Allowed on a login node from an existing registry: `singularity build img.sif docker://...`.
  - Converting a sandbox to `.sif` is allowed.
  - Not possible: building from a definition file (needs root; build elsewhere and copy in), sandbox mode, fakeroot.
- Authorised directory:
  - Images must be copied into `$SINGULARITY_ALLOWED_DIR` with `idrcontmgr cp my.sif`. The command runs a security check first.
  - Other commands: `idrcontmgr ls`, `idrcontmgr rm my.sif`.
  - The directory is unique per user, cannot be changed, and holds **20 containers** max.
- Running:
  - `singularity shell` / `run` requires an interactive session on a compute node.
  - Batch use: `srun singularity exec --nv $SINGULARITY_ALLOWED_DIR/img.sif python x.py`.
  - `--nv` enables the NVIDIA GPUs.
  - MPI: `srun --mpi=pmix_v2` or `pmix_v3`, depending on the MPI inside the container.
  - `--bind host:cont` mounts host directories.
  - Network: host network only. No ipvlan, macvlan or bridge.
- Jupyter and TensorBoard cannot be launched from a container.
- Not documented: whether `singularity exec` of an image outside `$SINGULARITY_ALLOWED_DIR` is blocked on login nodes.

Sources:
- http://www.idris.fr/docs/jean-zay/environnement/conteneurs

## 7. Software

- Environment Modules 4.3.1. Main commands:
  - `module avail [name]`, `module show`, `module load`, `module list`, `module purge`.
  - `idr_module_search [--arch cpu|v100|a100|h100] [-f requirements.txt] pkg ...` finds which IDRIS module contains given Python packages.
- Default modules target CPU and V100. A100 needs `module load arch/a100` first; H100 needs `module load arch/h100` first. This applies in batch scripts and in the terminal when compiling.
- AI environments are conda envs wrapped in modules, e.g. `pytorch-gpu/py3/2.8.0` (the documented default).
  - Loading one pulls in its dependencies, e.g. `gcc/11.4.1`, `cuda/12.8.0`, `nccl/2.27.3-1-cuda`, `cudnn/9.10.2.21-12-cuda`.
  - `pytorch-gpu/py3/2.13.0` (CUDA 13, H100 only) exists since 2026-08-24: `module load arch/h100 pytorch-gpu/py3/2.13.0`.
- Conda behaviour:
  - Loading the module runs `conda activate`.
  - `module purge`, `unload` and `switch` do **not** deactivate conda. Run `conda deactivate; module purge; module load ...`.
  - Two conda modules, or a module plus a personal env, cannot be active together.
- Preference order, per the docs:
  1. Ask assist@idris.fr to add the package to the module.
  2. `pip install --user --no-cache-dir <pkg>` on top of a module.
  3. Personal `conda create`, loaded from a python module. No Anaconda or Miniconda install is needed.
- pip location:
  - `pip install --user` defaults to `$HOME/.local`, which risks the HOME quota.
  - Fix: `mkdir $WORK/.local; ln -s $WORK/.local $HOME`. Use the same pattern for `$HOME/.conda`.
  - Without `--user`, the install fails: the system env is read-only.
  - Executables land in `.local/bin`. Use `export PATH=$WORK/.local/bin:$PATH` on compute nodes.
  - When alternating modules, set a different `PYTHONUSERBASE` per module, e.g. `$WORK/.local_tf240`, before installing and before running.
- `mpi4py` needs an MPI module loaded (`module avail openmpi`). No MPI module is loaded by default.
- Personal conda envs are a common cause of HOME quota overrun.
- After the RHEL 9.6 update, system GCC is 11.5.0 and `gcc/11.4.1` is an alias of `gcc/11.5.0`.

Sources:
- http://www.idris.fr/docs/jean-zay/environnement/environment-modules
- http://www.idris.fr/docs/jean-zay/logiciels_bibliotheques/python
- http://www.idris.fr/docs/jean-zay/logiciels_bibliotheques/logiciels_ia
- http://www.idris.fr/docs/jean-zay/nouvel-utilisateur
- http://www.idris.fr/blog/nouveau-module-pytorch-2.13
- http://www.idris.fr/blog/migration-red-hat-9-6

## 8. Policies

- Login nodes are for compiling, preparing scripts and submitting jobs. No GPUs.
  - Interactive page: 5 GB RAM shared by all of a user's processes; 30 min CPU time per process.
  - New-user page: 1 CPU per user; 30 min CPU time per process.
  - Doc inconsistency between the two: memory limit vs CPU-count limit.
  - What happens when the limits are hit (kill or throttle) is not documented.
- Running code interactively must go through `srun` or `salloc` on compute nodes.
- A batch job is preferred for heavy work: it survives a lost connection or a login node crash.
- Allocated but idle interactive jobs are charged until `--time`.
- SCRATCH: no artificial lifetime extension (e.g. touching files). Delete useless files, archive to WORK or STORE (Flash Info 2026-07).
- Connection:
  - SSH only from machines registered in the IDRIS filters: **fixed institutional IPs only**, no personal or dynamic IPs.
  - Add or remove IPs with the FGC form, signed by the user and the lab security officer, sent to gestutil@idris.fr.
  - When away: use the lab VPN (its IP must be registered) or a registered jump host (`ssh -J login_rebond@rebond login@jean-zay.idris.fr`).
  - Abroad: temporary access via the FGC form.
- Hosts: `jean-zay.idris.fr` (login), `jean-zay-pp.idris.fr` (prepost login). Host key fingerprints are published on the SSH page.
- SSH keys are allowed. IDRIS asks users to test SSH certificates (`idr_keygen`):
  - `-t interactive`: valid 1 year, passphrase of at least 20 characters.
  - `-t transfert-only`: valid 7 days, no passphrase.
  - Known issue: "certificates do not seem to work on macOS". Certificates are not supported on prepost nodes.
- Only `bash` is supported as login shell. Accounts are personal and must not be shared.
- The first connection must be over SSH before JupyterHub can be used.
- Maintenance happens about once a week on average. Status page: http://www.idris.fr/docs/statut-machines (not read).

Sources:
- http://www.idris.fr/docs/jean-zay/slurm/exec_interactif
- http://www.idris.fr/docs/jean-zay/nouvel-utilisateur
- http://www.idris.fr/docs/jean-zay/gestion-compte/connexion-ssh
- http://www.idris.fr/docs/dari/gestion-des-acces-idris
- http://www.idris.fr/docs/faq/faq
- http://www.idris.fr/blog/flash-info-2026-07

## 9. Pitfalls stated in the docs

1. The default `--time` is 10 min on compute partitions. Set it explicitly and keep it within the QoS limit. A job asking more than the QoS allows pends with `QOSMaxWallDurationPerJobLimit`. Cancel and resubmit.
2. Jobs pending with `QOSGrpCpuLimit` or `QOSGrpGRES` (t4) are valid. Do not cancel them.
3. Forgetting `--account=<proj>@<type>` when it is required charges the wrong allocation.
4. `--cpus-per-task` above the per-GPU ratio bills extra GPUs. Below the ratio, CPU memory is limited and CPU-side OOM is likely. The default is 1.
5. Any multi-node job is exclusive and billed as whole nodes.
6. Without `module purge`, the login shell modules leak into the job. Conda also needs `conda deactivate`.
7. gpu_p5 jobs fail with "Illegal Instruction" when using default (Intel) modules or binaries. Load `arch/a100` and recompile. The FAQ says `module load cpuarch/amd`; other pages say `arch/a100` (doc inconsistency).
8. H100: load `arch/h100`. CUDA below 12.0 does not work there.
9. STORE is not mounted on compute nodes. Use archive or prepost jobs chained with `--dependency`.
10. JOBSCRATCH differs between chained jobs. Share data through SCRATCH or WORK.
11. SCRATCH purge uses file timestamps. Extracted archives keep old dates and get purged early. Use `tar -m` or `unzip -DD`. No purge notification exists.
12. WORK is not backed up. Keep archives of important data on STORE.
13. Quota hit: no email, running jobs can fail, editing can zero a file. Quota numbers are a day old.
14. pip and conda default to `$HOME/.local` and `$HOME/.conda`, which fills the 3 GB HOME. Symlink them to WORK.
15. Editing the job output file while the job runs can disturb the job.
16. Jobs are requeued and restart from scratch after hardware incidents unless `--no-requeue` is set.
17. `salloc` keeps the shell on the login node. Run work with `srun`.
18. Poll `squeue` at most 1 to 2 times per minute.
19. Python: use `python -u` for unbuffered output in batch logs.
20. Keep directories to a few tens of thousands of entries at most.
21. While a job is PENDING, `scontrol show job` may show half the memory with nomultithread.
22. Hardcoded paths from the 2024 filesystem migration (`/gpfswork/...`, `/gpfs7kw/linkhome/...`) and symlinks pointing to them must be redone with `$WORK` and `$HOME`.
23. DSDIR FineWeb moves from v1.0.0 to v1.4.0 on 2026-11-02 (`$DSDIR/HuggingFace/fineweb`).

Other doc inconsistencies:
- The FAQ says to test SSH certificates "at least until the end of February 2023" (stale).
- The FAQ counts 5 storage spaces; the storage page counts 4 plus DSDIR.
- The A100 example comment says "octo-GPU H100" (typo).
- The CPU partition text says about 160 GB usable per node; the memory page says 156 GB.

Sources: all URLs above, in particular
- http://www.idris.fr/docs/faq/faq
- http://www.idris.fr/docs/jean-zay/slurm/exec_batch
- http://www.idris.fr/docs/jean-zay/slurm/exec_alloc-mem
- http://www.idris.fr/docs/jean-zay/environnement/espaces-disques-quota
- http://www.idris.fr/docs/jean-zay/slurm/exec_multi-etapes
- http://www.idris.fr/blog/flash-info-2026-07

## Not documented or not found

- CUDA compute capability of each GPU.
- An Apptainer module.
- Max job array size.
- How prepost nodes get internet access.
- What enforces the login node limits (kill or throttle).
- Whether whole-node accounting for gpu_p6 is 4 GPUs (missing from the hours page).
- A multi-node H100 example script.
- GPU memory of the prepost V100 and the visu P6000.
