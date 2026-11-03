---
name: ag-compute
description: Submit and size jobs on the user's compute sites (CC-IN2P3, CRIANN Austral, Jean Zay, Dalia, Adastra) - probe node availability first, estimate time and resources, pick the partition with the earliest start. Use before any sbatch, or when asked where to run a heavy job, why a job is stuck in the queue, or which site or allocation to use.
---

Run from the laptop over ssh. No agent runs on a compute site. Site reference: `drafts/<site>.md`, from official docs, not yet checked against the machines unless noted below.

## Before every submission

1. **Probe.** A job that cannot start waits without error.
   ```bash
   sinfo -h -o "%P %a %l %c %m %D %T"            # states per partition: idle or mixed nodes, or all draining?
   sbatch --test-only -A <acct> -p <part> -c <n> --mem=<m> -t <t> --wrap=true    # refused, or expected start
   scontrol show node <node> | grep Reason       # why a node is out, if most are
   squeue -u $USER                               # what is already queued
   ```
2. **Estimate.** Time, memory and CPUs from a measured run of the job or a stated scaling. Request about 1.5 times the estimate, not the partition maximum. Say the estimate and its source when reporting the job.
3. **Choose.** The earliest start that fits, across sites. All nodes draining means change site.
4. **Allocation.** A shared allocation for another project needs the user's agreement.
5. **After submitting.** Read the state and reason in `squeue`. A pending job with `ReqNodeNotAvail` or no start time gets probed, then moved or cancelled.
6. **After the first run.** Compare `sacct -o Elapsed,MaxRSS` with the request, and resize the next submission.

Traveling or flaky link: all state on the site, under `sbatch`. Resumable copies (`rsync --partial`) with bounded retries. No job depends on the laptop.

## Environment

`uv` from the official release, checksum verified, in `~/.local/bin`. Compute nodes may lack network: sync environments on the login node. Check free space in the home before large environments, since the locked Linux torch brings GPU libraries.

## Checked on the machines

- **CC-IN2P3** (`cca`): account `ganil` refuses jobs with `AssocGrpSubmitJobsLimit`; account `m4cast` is accepted, with the user's agreement for LIONS. No `uv` in the base system. The login profile sets `HTTPS_PROXY=http://localhost:8888`, which does not respond: unset it for network access. Rolling kernel updates can drain every partition at once (2026-11-02).
- **CRIANN Austral** (`criann`): account `2024028` (`ac` is refused by `sbatch`). CPU partitions `debug`, `2tcourt`, `tcourt`, `court`, `long`, `tlong`; there is no `cpu` partition for this group. Hours are charged on reserved cores times elapsed time. Login nodes cap virtual memory at 24 GB per process and show 384 cores, so `uv` aborts with a memory error unless pinned (`taskset -c 0-7 uv ...`). Compute nodes reach PyPI and pytorch.org. `debug` (30 min) started within minutes on 2026-11-02 while `2tcourt` showed about 1.5 h. `sacct` MaxRSS came back empty for short jobs on 2026-11-02.
- **Dalia, lxplus**: key refused from the laptop (2026-11-02). **Jean Zay**: banner timeout (2026-11-02). Feynman: credentials to recover.
