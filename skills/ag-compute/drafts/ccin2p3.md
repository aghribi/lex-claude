# CC-IN2P3 (Lyon): jobs reference

Pages read: 2026-10-31, English user doc (`https://doc.cc.in2p3.fr/en/...`), French versions cross-checked for the login rules, AI policy and GPU syntax (same content).
Not logged in to any machine. Doc warns that example outputs (`sinfo`, `scontrol`, `sacctmgr`) are format examples only: run them on a login server for current values.

Inaccessible: `https://cctools.in2p3.fr/mrtguser/info_slurm_parcV2.php` ("Informations about slurm batch system", the page the doc points to for node hardware): HTTP 403. User portal (`portail.cc.in2p3.fr`) needs login, not read.

## 1. Machines

### Login clusters

| Alias | Use | Notes |
|---|---|---|
| `cca.in2p3.fr` | General purpose: prepare, develop, test jobs | Alias to least loaded server (e.g. `cca042`) |
| `ccahm.in2p3.fr` | Same use, large RAM | Local SSD `/scratch_ssd` plus `/scratch` (shared across login clusters) |

- `ssh -Y <username>@cca.in2p3.fr` (X11 trusted forwarding).
- Scheduler: Slurm (example node output shows Slurm 25.05.3, RHEL 9 kernel `el9_6`; example only).

### Partitions (from the doc's example `sinfo`, node counts may have changed)

| Partition | Example nodes | Purpose |
|---|---|---|
| `htc` (default) | 268, `ccwslurm[...]` | Single and multi-core jobs, 1 node per job |
| `htc_arm` | 4, `ccwslurma[0003-0006]` | ARM processors, htc limits |
| `htc_interactive` | 2, `ccwislurm[0001-0002]` | Interactive |
| `htc_highmem` | 1, `ccwmslurm0001` | Jobs above ~200G memory |
| `htc_daemon` | 1, `ccwslurm0001` | Long, light monitoring/orchestration jobs |
| `flash` | 1, `ccwslurm0001` | Whole node for test/debug, 1 h |
| `hpc` | 8, `ccwpslurm[0017-0024]` | MPI over InfiniBand, multi-node |
| `hpc_interactive` | named in text, not in example `sinfo` | Interactive HPC |
| `gpu_v100` | 16, `ccwgslurm[0100-0115]` | GPU batch |
| `gpu_v100_interactive` | 1, `ccwgislurm0100` | GPU interactive |
| `gpu_h100` | 3, `ccwgslurm[0200-0202]` | GPU batch |
| `gpu_h100_interactive` | 1, `ccwgislurm0200` | GPU interactive |

### Node hardware

| Item | Documented value |
|---|---|
| htc example node `ccwslurm0002` | x86_64, 64 CPUs, ThreadsPerCore=1, RealMemory 192000 MB, MemSpecLimit 6000, DefMemPerCPU 1024 (partition) |
| htc partition total (example) | 21312 CPUs, 268 nodes |
| CPU models | not documented (hardware page 403) |
| GPU models | NVIDIA V100 and H100 (partition names, "two GPU types") |
| GPUs per node | not documented ("up to the limit of GPUs in the corresponding node") |
| GPU memory | not documented |
| CPU/GPU ratio | not documented as a number; rule given in section 3 |
| GPU architecture / compute capability | not documented by CC. [UNVERIFIED, NVIDIA general knowledge, not CC doc]: V100 = Volta sm_70, H100 = Hopper sm_90 |
| FP64 capability | not documented |
| CUDA version | one version installed, matched to the driver; check with `nvidia-smi` on an interactive GPU node. Number not documented |
| nvcc path | `/usr/local/cuda-12/bin/nvcc` (doc); example script uses `/usr/local/cuda/bin/nvcc` |
| Stack | drivers, CUDA, cuDNN, NCCL, CUPTI provided |

Sources:
- https://doc.cc.in2p3.fr/en/Daily-usage/cca-connect.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/configuration.html
- https://doc.cc.in2p3.fr/en/Computing/computing-introduction.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/hpc-env.html
- https://gitlab.in2p3.fr/ccin2p3-support/utilities-examples/examples/slurm-scripts (scripts/gpu_cudnn.sh)
- https://cctools.in2p3.fr/mrtguser/info_slurm_parcV2.php (403, not read)

## 2. Access and accounts

- Account required: a "computing account" = user account member of a collaboration authorised to use CC resources. Without it: no login servers, no compute, no storage.
- Login: 12 chars max, first letter of first name + first 11 letters of last name. Not customisable.
- Group vs account: group = Unix group (collaboration); account = Slurm entity charged.
- Default Slurm account = user's main Unix group. Override per job with `-A | --account=`, or change main group (`newgroup [--temp|--login] <group>`, or Identity Management Portal). `newgroup` can fail if the Kerberos ticket expired.
- List accounts and allowed QoS: `sacctmgr show user withassoc <username> format=Account,QOS%50`.
- QoS is set automatically from the partition: set the partition only.
- GPU access: "restricted and depends on the resources request made by your computing group". Contact user support.
- Resources are requested yearly (last quarter, answer before end of December). GPU requested in hours, HTC/HPC in HS23.h. No tacit renewal: without a new request the group "could no longer be able to compute".
- Per-group cap on simultaneously used resources (from the yearly request). See "Jobs of your groups" on the User portal. Reaching it: jobs pend. `AssocMaxSubmitJobLimit` at submit or `(AssocMaxJobsLimit)` in squeue: "you have probably been blocked", check inbox or contact support.
- Account and collaboration membership expire; renewal notices start 90 days before. 3-month grace period for account revalidation.

Sources:
- https://doc.cc.in2p3.fr/en/Daily-usage/users.html
- https://doc.cc.in2p3.fr/en/Daily-usage/management.html
- https://doc.cc.in2p3.fr/en/Daily-usage/resources.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/configuration.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/environment.html

## 3. Slurm specifics

### Mandatory options
- `-t` (time), `-c` (CPUs per task), `--mem`: submission refused if any is missing.
- `--mem` takes non-zero integers only: `--mem=5500M`, not `--mem=5.5G`. Bare number = MB.
- `-L` declares storage and licensed software used: e.g. `-L sps`, `-L sps,matlab`. List: `scontrol show lic | grep default`; group limits: `scontrol show lic | grep -A1 <group>`. Omit `_default` / `_<group>` suffixes on the command line.
- Time formats: `minutes`, `minutes:seconds`, `hours:minutes:seconds`, `days-hours`, `days-hours:minutes`, `days-hours:minutes:seconds`.
- Working directory = submission directory (not TMPDIR). Change with `-D`.
- `--mail-user` must be a valid professional address; do not enable auto-replies during the job.

### QoS and limits (example `sacctmgr show qos`)

| QoS | Used with | MaxWall | Max submitted / user | MaxTRES |
|---|---|---|---|---|
| normal | htc, htc_arm, htc_highmem, hpc | 7-00:00:00 | 5000 | |
| htc | htc | | | mem=150G |
| flash | flash | 01:00:00 | 10 | mem=150G |
| gpu | gpu_*, gpu_*_interactive | 7-00:00:00 | 100 (simultaneous jobs) | |
| daemon | htc_daemon | 90-00:00:00 | 10 | cpu=1, mem=16G |
| interactive | *_interactive | 7-00:00:00 | 4 sessions | |
| dask | htc (Jupyter platform) | 2-00:00:00 | | priority 1000 |

Per-partition resource rules:
- `htc`: 1 node; CPU = node hardware; memory 150 GB.
- `htc_highmem`: CPU and memory = node hardware. Rule of thumb: >200G goes here.
- `htc_daemon`: 1 CPU, 16 GB.
- `flash`: same CPU/memory as htc, 1 h.
- `hpc`: may span nodes; limits = whole HPC platform. `-n` beyond one node's CPUs overflows to a second node even without `-N`.
- `gpu_*`: 1 node. Memory as `htc_highmem`. CPU limit tied to GPUs requested: max CPUs per GPU = lowest CPU/GPU ratio among nodes of that partition (doc example: nodes at 5 and 6 CPU/GPU, limit 5 per GPU). Actual ratios not documented.

### GPU request syntax (as documented)
- Type selected by partition, count by `--gpus N`:
  - `sbatch -t 0-01:00 -c 1 --mem 10G -p gpu_h100 --gpus 1 job.sh`
  - `sbatch -t 0-01:00 -c 1 --mem 10G -p gpu_v100 --gpus 1 job.sh`
- Any type, first available: list both partitions: `-p gpu_v100,gpu_h100 --gpus 1` (interactive: `-p gpu_v100_interactive,gpu_h100_interactive`).
- Typed GRES (`--gpus h100:1`, `--gres=gpu:h100:1`) at submission: not documented. Only GRES use found: job steps inside a job, `srun --gres gpu:1 --exclusive --mem 2500 -n 1 ...` (official example repo).
- Submit filter: not documented as such. Observed in doc output: `sbatch: INFO: Account ...`, `Partition set to: htc`, `Partition limited to one node per job`, `Time limit set to ...`. Its rules on GPU syntax: not documented.

### Interactive
- CPU: `srun -p htc_interactive -t 0-08:00 -c 4 --mem 2G --pty bash -i`
- GPU: `srun -t 0-08:00 --mem 2G -p gpu_h100_interactive --gpus 1 --pty bash -i` (doc example omits `-c`, although `-c` is listed as mandatory for submission).
- `salloc`: not documented.
- Max 4 interactive sessions per user.
- Compile CUDA on an interactive GPU node, then exit and submit with sbatch.

### Job arrays
- `sbatch -t 0-00:30 -c 1 --mem 2G --array=0-3 job.sh`; list syntax `--array=0,6,16-32`.
- Variables: `SLURM_ARRAY_JOB_ID`, `SLURM_ARRAY_TASK_ID`, `SLURM_ARRAY_TASK_COUNT`, `SLURM_ARRAY_TASK_MAX`, `SLURM_ARRAY_TASK_MIN`. Max array size: not documented.

### Long jobs
- `htc_daemon`: `sbatch -p htc_daemon -t 90-00:00 -c 1 --mem 1G job.sh`.
- Beyond 7 days: self-resubmitting script, `sbatch --dependency=afterany:$SLURM_JOBID my_batch_script.sh` near the top.
- Pipelines: `--dependency=after|afterany|afternotok|afterok:<id>` or `singleton`.

### Example: CPU (doc, trimmed)
```bash
#!/bin/bash
#SBATCH --job-name=serial_job_test
#SBATCH --output=serial_test_%j.log
#SBATCH --partition=htc
#SBATCH --cpus-per-task=1
#SBATCH --ntasks=1
#SBATCH --mem=2000
#SBATCH --time=1-00:00:00
#SBATCH --licenses=sps
set -euxo pipefail
module load python
python my_python_script.py
```
Multi-CPU: set both `--cpus-per-task` and `--mem-per-cpu`, otherwise sub-processes may all run on one CPU.

### Example: 1 GPU (official repo `scripts/gpu_101.sh`)
```bash
#!/bin/bash
#SBATCH --job-name=gpu_101
#SBATCH --output=output_%x_%j.log
#SBATCH --cpus-per-task 1
#SBATCH --time 0-00:01
#SBATCH --partition gpu_v100
#SBATCH --gpus 1
#SBATCH --mem 1000
set -euo pipefail
nvidia-smi
```

### Example: 2 GPUs, one per step (official repo `scripts/gpu_matrixmul.sh`, trimmed)
```bash
#!/bin/bash
#SBATCH --cpus-per-task 5
#SBATCH --time 0-00:05
#SBATCH --partition gpu_v100
#SBATCH --gpus 2
#SBATCH --mem 5000
#SBATCH --ntasks 2
set -euo pipefail
export CUDA_VISIBLE_DEVICES=0
srun --gres gpu:1 --exclusive --mem 2500 -n 1 ./matrixMul ... &
export CUDA_VISIBLE_DEVICES=1
srun --gres gpu:1 --exclusive --mem 2500 -n 1 ./matrixMul ... &
wait
```
Single-process multi-GPU (DDP-style) example: not documented. Multi-node GPU: not allowed (gpu_* = 1 node).

### Monitoring
- `seff <jobid>`: samples ~every 30 s, so "Memory Utilized" is the max of samples, not the true peak. Use job profiling for accuracy.
- Prefer suspending and modifying a misconfigured job over cancelling it.

Sources:
- https://doc.cc.in2p3.fr/en/Computing/slurm/submit.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/use-syntax.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/environment.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/configuration.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/hpc-env.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/monitor.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/best-practices.html
- https://gitlab.in2p3.fr/ccin2p3-support/utilities-examples/examples/slurm-scripts (scripts/gpu_101.sh, gpu_matrixmul.sh, gpu_cudnn.sh)

## 4. Storage

| Area | Path / variable | Default quota | Backup | Purge | On compute nodes |
|---|---|---|---|---|---|
| HOME (PBS) | `/pbs/home/<u>/<username>`, `$HOME` | 20 GiB | Daily; snapshots at noon and midnight, kept 3 months, in `.snapshot` (hidden), `$HOME_BACKUP` | none documented | yes |
| THRONG (PBS) | `/pbs/throng/<group>`, `$THRONG_DIR` | 100 GiB, on request to support | as HOME | none documented | yes |
| GROUP (SPS) | `/sps/<group>` | 5 TiB for new group | no (very few exceptions) | files not accessed for >2 years deleted | yes; declare `-L sps` |
| Job TMPDIR | `/scratch/slurm.<jobid>.<taskid>/tmp`, mounted as `/tmp`, `TMPDIR=/tmp` | not documented | no | deleted at job end | node-local |
| Login `/scratch` | `/scratch/$USER` (create it) | not documented | no | normally after 14 days, may be deleted any time | no (login servers) |
| ccahm `/scratch_ssd` | local SSD on ccahm | not documented | no | not documented | no |

- Quotas: `df -h <path>`, `spsquotalist`, `fs4 listquota`. PBS quota extension via support.
- Full HOME causes job errors.
- PBS ACLs: `fs4 setacl/recsetacl`. `chmod` and some editors (vi, emacs) wipe NFSv4 ACLs.
- SPS extra space: funded request, or both "75% rules" (space ≥75% full, ≥75% of used space accessed in last 12 months).
- SPS suits large files, many small writes, files shared between jobs, many files.
- Node `/scratch` is shared by jobs on the node: clean TMPDIR at job end. Use TMPDIR for heavy I/O, copy repeatedly read files there. Pass data between jobs via THRONG or SPS, not node scratch.
- Every collaboration must file a Data Management Plan (https://dmp.in2p3.fr/).

Sources:
- https://doc.cc.in2p3.fr/en/Data-storage/storage-areas.html
- https://doc.cc.in2p3.fr/en/Data-storage/distributed-filesystems/pbs.html
- https://doc.cc.in2p3.fr/en/Data-storage/distributed-filesystems/sps.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/environment.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/best-practices.html
- https://doc.cc.in2p3.fr/en/Daily-usage/cca-connect.html
- https://doc.cc.in2p3.fr/en/Daily-usage/resources.html

## 5. Network

- Internet access from login nodes: not documented explicitly. Doc examples run `wget` of the CUDA installer and `pip install` from PyPI / download.pytorch.org, implying outbound HTTP(S) works where those commands are run (location not stated). [UNVERIFIED]
- Internet access from compute nodes: not documented.
- HTTP(S) proxy for batch jobs: not documented ("proxy" in the doc refers only to grid certificate proxies for dCache).
- Only SSH allowed for connections and transfers to/from login servers (scp, sftp, rsync). Password or Kerberos (GSS-API). SSH keys work but do not create a Kerberos ticket.
- Policy constraint on outbound use: non-institutional services (remote storage, non-contracted AI) forbidden "on and from" CC platforms (section 8).

Sources:
- https://doc.cc.in2p3.fr/en/Network/connectivity.html (institutional network only, nothing on node egress)
- https://doc.cc.in2p3.fr/en/Daily-usage/cca-connect.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/hpc-env.html
- https://doc.cc.in2p3.fr/en/Computing/jnps/kernels.html
- https://doc.cc.in2p3.fr/en/Daily-usage/users.html

## 6. Containers

- Apptainer on all login and compute servers. Default = latest EPEL release (WLCG recommendation); other releases via `module`. `singularity` wrapper exists but is unmaintained and may be removed.
- GPU: `apptainer exec --nv [options] [image] [script]`.
- `$HOME` is not mounted automatically (differs from default Apptainer). Bind explicitly; doc suggests binding `/pbs` root to get HOME and THRONG: `--bind /pbs`. SPS: `--bind /sps/<group>:/sps` (official images provide `/sps` and `/srv` mount points).
- Official images: `/cvmfs/singularity.in2p3.fr/images/{HTC,HPC}/` (HPC includes GPU images).
- Own images allowed. Store on storage with good I/O, avoid compressed archives. CVMFS stratum-0 area for user images on request to support. Non-official images not guaranteed.
- Building needs root: build elsewhere (e.g. workstation), copy to storage, run in job.
- Docker images can be invoked/converted by Apptainer.
- Cache location (`APPTAINER_CACHEDIR`) guidance: not documented.
- CUDA in container: allowed, must respect driver/CUDA support matrix.

Sources:
- https://doc.cc.in2p3.fr/en/Software/apptainer.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/hpc-env.html

## 7. Software

- Environment Modules: `module avail|view`, `module load Category/software/version`, `module list`, `module purge`, `module save/restore`. `ml` alias.
- `module: command not found` in scripts: `source /etc/profile.d/modules.sh` or shebang `#!/bin/bash -l`.
- CC module config: `module config rcfile /pbs/software/modulefiles/redhat-9-x86_64/modulerc`.
- R/Python/Julia package installs default to `/pbs/software` (not writable): set an install target.
- Python: several releases via modules; venv: `python -m venv --system-site-packages <env>`.
- conda: Anaconda ToS. Avoid channels `pkgs/main`, `pkgs/r`, `pkgs/msys2`. Recommended: Miniconda or Micromamba with `.condarc`:
  ```
  channels:
  - nodefaults
  - conda-forge
  channel_priority: strict
  ```
  Use `--prefix` on shared storage (environments are large).
- Jupyter kernels page: managed environments via uv (Python only), conda or pixi; "In general, pixi is preferred". conda distributions "consume significant disk space and do not always handle application dependencies very well".
- Explicit "central anaconda module deprecated" statement: not found. The doc still shows `module load Programming_Languages/anaconda/3.9` in a kernel example.
- CUDA versions other than the installed one: install toolkit in `$THRONG_DIR`, use an Apptainer image, or use pip-provided CUDA (e.g. `pip install torch ... --index-url https://download.pytorch.org/whl/cu128`, `pip install -U "jax[cuda13]"`). Validate with a small GPU computation.
- Licensed software (Matlab, IDL, LabVIEW) needs `-L` tokens.

Sources:
- https://doc.cc.in2p3.fr/en/Software/software-introduction.html
- https://doc.cc.in2p3.fr/en/Software/modules.html
- https://doc.cc.in2p3.fr/en/Software/python.html
- https://doc.cc.in2p3.fr/en/Software/conda.html
- https://doc.cc.in2p3.fr/en/Computing/jnps/kernels.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/hpc-env.html

## 8. Policies

Login servers (non-compliance: processes may be killed):
- 1 computing process per login server, 3 per cluster.
- Max 24 h CPU time per process, 1 h CPU time for a multi-core process. Processes idle >24 h killed.
- No parallel CPU+I/O-heavy processes (`make -j`, scons, b2, ninja): use interactive jobs.
- No batch-style work (loops over many files).
- Heavy memory: use `ccahm`.
- 1 transfer process per server (scp, rsync, dq2-get), 3 across all login servers.
- No detached/persistent processes after logout. `screen` tolerated, not as batch substitute, service host or way to hold GPU interactive nodes.
- rmate-like editors: random TCP port.

AI and external services:
- Only services/software validated and deployed by CNRS and CC-IN2P3. Non-institutional services forbidden on and from CC platforms, in particular remote storage and AI services without CNRS contract.
- Authorised AI tools: Emmy (Mistral), French government tools such as Albert. Other AI agents/assistants are therefore not authorised (doc does not name products).

IDE servers (VS Code and derivatives: Antigravity, Cursor, Positron, Zed, VSCodium):
- Allowed with rules: connect to a specific server (`cca042.in2p3.fr`), not the `cca` alias.
- Do not run `srun` interactive sessions in a VS Code terminal (orphaned allocations).
- Do not launch the VS Code integrated Jupyter on login servers (killed); use the Jupyter platform.
- Disable or tame ripgrep (`"search.useRipgrep": false`); set `files.watcherExclude`; keep project dirs small.
- Ghost Node.js after disconnect is detected and killed.

Fair share: not documented. Documented: per-group concurrent-resource cap from the yearly request; platform favours small jobs (>85% of jobs use 1 CPU and <4 GB); memory is often the limiting factor.

Acknowledgement text for publications: "We gratefully acknowledge support from the CNRS/IN2P3 Computing Center (Lyon - France) for providing computing and data-processing resources needed for this work."

Sources:
- https://doc.cc.in2p3.fr/en/Daily-usage/cca-connect.html
- https://doc.cc.in2p3.fr/en/Daily-usage/users.html
- https://doc.cc.in2p3.fr/fr/Daily-usage/users.html
- https://doc.cc.in2p3.fr/en/Daily-usage/vs-code.html
- https://doc.cc.in2p3.fr/en/Computing/computing-introduction.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/environment.html

## 9. Pitfalls (from the docs)

- Missing `-t`, `-c` or `--mem`: job refused.
- Fractional `--mem` (`5.5G`) not accepted.
- Forgetting `-L sps` for jobs reading SPS.
- Requests above node hardware (`CPUTot`, `RealMemory`) never run: check `scontrol show node`.
- >150G on htc refused: use `htc_highmem`.
- gpu_*: CPUs capped by the partition's lowest CPU/GPU ratio.
- Only one CUDA version on GPU nodes; old CUDA unsupported by the driver. Check the NVIDIA support matrix.
- Apptainer does not mount `$HOME`; bind `/pbs`. Add `--nv` for GPUs.
- Full HOME breaks jobs writing there.
- TMPDIR deleted at job end; node `/scratch` shared, clean it.
- Login `/scratch` purged (~14 days, or any time).
- SPS: no backup, files unread for 2 years deleted.
- chmod / vi / emacs wipe NFSv4 ACLs on PBS.
- `newgroup` fails with expired Kerberos ticket. SSH key login does not give a Kerberos ticket.
- `seff` memory is sampled, underestimates peak.
- `AssocMaxSubmitJobLimit` / `AssocMaxJobsLimit`: possibly blocked by admins.
- Group stops computing if the yearly resource request is not renewed.
- Doc errors to be aware of: array example says `SLURM_ARRAY_TASK_MAX`=0 and `MIN`=3 (swapped); CUDA install example installs to `$THRONG_DIR/cuda-12.4` but exports `$HOME/cuda-12.4` paths.

Sources:
- https://doc.cc.in2p3.fr/en/Computing/slurm/submit.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/use-syntax.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/environment.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/configuration.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/hpc-env.html
- https://doc.cc.in2p3.fr/en/Computing/slurm/monitor.html
- https://doc.cc.in2p3.fr/en/Software/apptainer.html
- https://doc.cc.in2p3.fr/en/Data-storage/storage-areas.html
- https://doc.cc.in2p3.fr/en/Data-storage/distributed-filesystems/pbs.html
- https://doc.cc.in2p3.fr/en/Data-storage/distributed-filesystems/sps.html
- https://doc.cc.in2p3.fr/en/Daily-usage/management.html
- https://doc.cc.in2p3.fr/en/Daily-usage/resources.html

## Not documented (gaps)

CPU models, GPU count per node, GPU memory, CPU/GPU ratios, compute capability, FP64, installed CUDA version, compute-node internet and proxy, typed GPU GRES syntax and submit-filter rules, salloc, max array size, fair-share/priority weights, Apptainer cache guidance, explicit deprecation notice for the central anaconda module.
