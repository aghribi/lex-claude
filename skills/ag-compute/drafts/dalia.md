# Dalia (IDRIS) reference

Pages read 2026-10-31. Official docs are public, in French only, under `http://www.idris.fr/docs/dalia/` (HTTP works; HTTPS to www.idris.fr timed out from this network on that date). The tree has 7 pages: presentation, hardware, acces-ressource, connexion, environnement, soumission, faq. Anything not on those pages is marked [UNVERIFIED] or "not documented".

## 0. What Dalia is

| Item | Value |
|---|---|
| Type | NVIDIA GB200 NVL72, first in service in Europe |
| Installed | IDRIS, summer 2025 |
| Operator | IDRIS (CNRS). GENCI system |
| Vendor | NVIDIA via Bull (IDRIS page) / Eviden (GENCI page) |
| Status | Prototype machine, for benchmarking and "Grand Challenge" projects |
| Network zone | Outside ZRR (no ministerial authorisation for accounts) |
| AI Factory link | GENCI page frames it within France's AI factory (AI2F) plans, with MIG partitioning and DGX Cloud Lepton listed as planned services, not current ones |

Sources: http://www.idris.fr/docs/dalia/dalia-presentation/ , http://www.idris.fr/docs/dalia/dalia-acces-ressource/ , https://www.genci.fr/en/node/346

## 1. Machines

| Item | Compute node | Login node |
|---|---|---|
| Count | 18 | not documented |
| CPU | 2x NVIDIA Grace (ARM Neoverse-V2), 72 cores each = 144 physical cores | 2x Intel Xeon Gold 6530, 32 cores each = 64 cores |
| RAM | 1.7 TB | 256 GB |
| GPU | 4x NVIDIA GB200 (Blackwell), HBM3e 186 GB each | none |
| Internet | yes | not stated |

- Architecture mismatch: login nodes are x86_64, compute nodes are aarch64. Build software on a compute node.
- Interconnect: one-level non-blocking InfiniBand fat-tree. GENCI adds a 72-GPU NVLink 5 domain (NVL72, NVLink switch, 13 TB federated memory).
- Storage network: DDN AI400X2 Turbo on converged Ethernet, 8x 200 GbE array links, 2x 200 GbE per compute node.
- Inconsistency in the docs: the hardware page says "64 GPU NVIDIA GB200", but also 18 nodes x 4 GPUs = 72. GENCI says 72 Blackwell GPUs and 36 Grace CPUs. Usable GPU count is unconfirmed.
- CUDA compute capability: not documented. Blackwell datacenter (B200/GB200) is sm_100 (CC 10.0) [UNVERIFIED, from memory, not on IDRIS pages]. Check with `nvidia-smi --query-gpu=compute_cap --format=csv` on a compute node.
- Partitions: not documented. `defq` (local note) [UNVERIFIED].
- Login hostname: `dalia.idris.fr`. Node name `dalia1` (local note) [UNVERIFIED].

Sources: http://www.idris.fr/docs/dalia/dalia-hardware/ , https://www.genci.fr/en/node/346

## 2. Accounts and access

| Step | Rule |
|---|---|
| Hours | DARI site (eDARI, https://www.edari.fr), **Dynamic Allocations (AD) only** |
| Selection | Strict, monthly. Justify why the GB200 technology matters to the project |
| Account | Created via eDARI, independent of Jean Zay. A Dalia account does not imply a Jean Zay account |
| Login format | `udlxxxxxx` |
| Required | Connection IP address + SSH public key |
| Key | `ssh-keygen -t ed25519 -f ~/.ssh/udlxxxxxx-DALIA -C " udlxxxxxx-DALIA"`, send the `.pub` to IDRIS |
| Hours questions | acces@genci.fr |
| Account questions | gestutil@idris.fr, subject prefixed `[Dalia]` |

Connection (only from the declared IP; fails until IDRIS installs the key in `authorized_keys`):

```
ssh -i ~/.ssh/udlxxxxxx-DALIA udlxxxxxx@dalia.idris.fr
```

`~/.ssh/config` (add `ProxyJump login_proxy@machine_proxy` if going through a gateway):

```
Host dalia
  Hostname dalia.idris.fr
  User udlxxxxxx
  ForwardX11 yes
  ForwardAgent yes
  IdentityFile ~/.ssh/udlxxxxxx-DALIA
```

- Accounting commands (consumption tracking, `idracct`-style): not documented.

Sources: http://www.idris.fr/docs/dalia/dalia-acces-ressource/ , http://www.idris.fr/docs/dalia/dalia-connexion/

## 3. Slurm

| Item | Value |
|---|---|
| Version | 24.11 (from the module name) |
| On the login node | `module load slurm/slurm/24.11` before any Slurm command, if not loaded by default |
| Commands | `sbatch`, `srun`, `squeue`, `scancel` |
| GPU syntax in docs | `--gpus-per-node=N` (max 4) in batch; `--gres=gpu:1` in `srun` |
| CPU per GPU in docs | 36 (144 / 4) |
| Mandatory options | not documented (no `--account`, `--partition` or `--qos` in the official examples) |
| Partitions, QoS, max walltime | not documented |
| Reservations | not documented (local note: used for events) [UNVERIFIED] |

Full node (official example, Apptainer):

```bash
#!/usr/bin/env bash
#SBATCH --job-name=test_dalia
#SBATCH --output=slurm_log/%x_%j.out
#SBATCH --error=slurm_log/%x_%j.out
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4      # max 4 GPU per node
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=36     # 4 x 36 = 144 CPUs
#SBATCH --time=0:40:00

cd $PROJECT_DIR
export APPTAINER_CACHEDIR=/lustre/work/<project_group>/<login>/<cache_directory>
srun apptainer exec --nv --pwd /my_project_dir --bind $PROJECT_DIR:/my_project_dir mon_container.sif <commande>
```

Note: `$PROJECT_DIR` is not defined by the system (the docs say no variable points to the work space). Set it yourself.

1 GPU: no official batch example. Built from the documented interactive line `srun --ntasks=1 --cpus-per-task=36 --gres=gpu:1 --hint=nomultithread --pty bash` [UNVERIFIED as a batch script]:

```bash
#!/usr/bin/env bash
#SBATCH --job-name=dalia_1gpu
#SBATCH --output=slurm_log/%x_%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=36
#SBATCH --hint=nomultithread
#SBATCH --time=0:40:00

WORK=/lustre/work/<project_group>/<login>
export APPTAINER_CACHEDIR=$WORK/.apptainer_cache
srun apptainer exec --nv --bind $WORK:$WORK $WORK/image.sif <command>
```

Sources: http://www.idris.fr/docs/dalia/dalia-soumission/ , http://www.idris.fr/docs/dalia/dalia-environnement/

## 4. Storage

All Lustre, 500 TB total.

| Space | Path | Variable | Quota |
|---|---|---|---|
| HOME | `/lustre/home/<login>` | `$HOME` | 3 GB, 12 000 inodes (increase on request) |
| WORK (user, per project) | `/lustre/work/<project_group>/<login>` | none, set `$WORK` in `~/.bashrc` | per project |
| WORK (shared) | `/lustre/work/<project_group>/shared` | none | per project, counted with user WORK |

- Inodes default to 3 000 per GB of requested volume.
- Exceeding either the volume or the inode quota blocks writes.
- Purge policy: not documented. Backups: not documented. Quota command: not documented.
- Visibility on compute nodes: not stated explicitly. The official job and conda examples use `/lustre/work/...` from compute nodes, consistent with a shared mount.

Source: http://www.idris.fr/docs/dalia/dalia-environnement/

## 5. Network

- Compute nodes have internet access (unlike Jean Zay).
- Login nodes: internet access not stated.
- SSH in only from the IP declared at account creation; use `ProxyJump` through a declared machine otherwise.
- Proxies or gateways for outbound traffic: not documented.

Sources: http://www.idris.fr/docs/dalia/dalia-hardware/ , http://www.idris.fr/docs/dalia/dalia-connexion/

## 6. Containers

- Apptainer is available and is the recommended way to work.
- GPU flag: `--nv`. Example also uses `--pwd` and `--bind`.
- Set `APPTAINER_CACHEDIR` under WORK to avoid HOME quota problems.
- Images must be aarch64 (ARM). An x86_64 image built for a laptop or another cluster will not run on compute nodes.
- Image location rules, allowed registries, build on site (`apptainer build`, fakeroot): not documented. Compute nodes have internet, so pulling on a compute node is possible [UNVERIFIED in practice].

Sources: http://www.idris.fr/docs/dalia/dalia-environnement/ , http://www.idris.fr/docs/dalia/dalia-soumission/

## 7. Software

- Modules (as on Jean Zay): compilers, CUDA libraries. `module avail` to list.
- Some modules load at login (see `module list` first thing). `module purge` can remove Slurm access.
- User-managed environments beyond the base stack: containers or conda.
- Conda: Miniforge aarch64, installed from a compute node, into WORK (not the default `$HOME/miniforge3`):

```bash
srun --ntasks=1 --cpus-per-task=36 --gres=gpu:1 --hint=nomultithread --pty bash
cd /lustre/work/<project_group>/<login>/
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh"
bash Miniforge3-Linux-aarch64.sh   # set prefix to /lustre/work/<project_group>/<login>/miniforge3
```

- PyTorch guidance, CUDA/driver versions, NGC images, `uv`: not documented. A PyTorch build needs aarch64 wheels with sm_100 kernels [UNVERIFIED].

Source: http://www.idris.fr/docs/dalia/dalia-environnement/

## 8. Policies and pitfalls

- Prototype machine: monthly strict selection, benchmarking / Grand Challenge scope only.
- x86 login vs ARM compute: compile and install on compute nodes.
- Load `slurm/slurm/24.11` on the login node; avoid `module purge`.
- HOME is 3 GB: put conda, caches, images in WORK.
- NCCL jobs on more than 11 nodes segfault with the default stack: add `ulimit -s 8192` (FAQ, citing NVIDIA NCCL troubleshooting).
- Support: assist@idris.fr, subject prefixed `[Dalia]`.
- Not documented: charter/usage rules specific to Dalia, job limits per user, data retention after project end.

Source: http://www.idris.fr/docs/dalia/dalia-faq/

## Local notes vs docs

| Local note | Docs |
|---|---|
| Login node `dalia1` | Only `dalia.idris.fr` documented |
| Partition `defq` | Not documented |
| 4x B200, 144 CPUs per node | 4x GB200 186 GB, 144 Grace cores: consistent |
| Lustre `/lustre/work/<project>` | `/lustre/work/<project_group>/<login>` and `/shared`: consistent |
| Reservations for events | Not documented |
| Apptainer `.sif` | Documented, `--nv` |
