# Working rules: laptop, code host, compute sites, data

Reference implementation: FCCee xsuite_heb, branch `v22` (`sites/`, `tools/site.sh`, `tools/xsh-submit`, `code/_job_env.sh`, `environment/`, `.gitlab-ci.yml`).

## Where things live

| What | Lives on | Moved by | Never |
|---|---|---|---|
| Code | code host (GitLab, GitHub) | `git push` / `git pull` (`tools/site.sh <site> deploy`) | sync client, rsync, copy |
| Environment | container image built by CI from `environment/` | `tools/site.sh <site> setup` | conda envs built by hand on a site, `~/.local` |
| Run state and results | compute site, one root per site | jobs write them | laptop, sync client |
| Small views (report HTML, chosen figures) | site, mirrored to the laptop | `rsync` pull, one direction | edited on the laptop |
| Documents | one sync client per folder (CERNBox or Nextcloud) | the sync client | two clients on one folder |
| Partner spaces | `cross_sync_active/` | sync client | other people's files edited |

The sync client (CERNBox) skips hidden files, so it never carries `.git`. `tools/git-state` (lex-claude) writes `GIT_STATE.md`, `.patch` and `.bundle` at each repo root every hour, so a clone can be rebuilt from the sync copy.

## Editing code

- On the laptop. On a site only on a branch committed and pushed from there.
- Never the same branch in two places without a pull.
- A job runs pushed code only: `submit` refuses a dirty or unpushed laptop branch and a site copy at another commit.

## Sites

One file per site, `sites/<site>.env`: ssh alias, scheduler (`slurm` or `condor`), clone path, container runtime and image directory, run-state and results roots, scheduler options per class (`prod`, `test`). Personal overrides in `sites/<site>.local.env` (gitignored). A new site is one more file.

From the laptop, the same commands for every site:

```bash
make deploy   SITE=<site>   # clone or fast-forward the site copy of the current branch
make setup    SITE=<site>   # install the image of this commit's recipe
make envcheck SITE=<site>   # image present, hash and package versions as in the lock
make submit   SITE=<site> OPTS=--test JOB=code/<job>.sh ARGS="KEY=VALUE ..."
make status   SITE=<site>
make logs     SITE=<site> ID=<jobid>
make index    SITE=<site>   # rebuild the site's run index
```

Job resources are one header line in each job script (`# XSH name= time= ntasks= cpus= mem= signal=`); `tools/xsh-submit` turns it into `sbatch` options or an HTCondor submit file. Every job script starts with `source _job_env.sh || exit 3`.

## Environment

- Recipe in `environment/`: Dockerfile (base image by digest), conda lock (explicit URLs + md5, conda-forge only: Anaconda `defaults` needs a paid licence in large organisations), pip lock (exact versions of the packages the code imports and their dependencies).
- Image tag = hash of the recipe (`tools/env-hash`). CI builds it when `environment/` changes and pushes it to the project registry.
- A job refuses an image whose hash differs from the recipe of its commit. Each run records the image and the versions of the physics packages.
- Upgrading a package (a new xtrack): edit the pip lock, push, wait for CI, `make setup` on each site, rerun the pilot, compare with the previous image before production.
- Branches with the same recipe share an image; an old branch keeps the image of its recipe.

## Validation of a new site or image

Run the pilot job (short, same parameters every time) and compare with the reference site: same datasets and shapes, same input hashes, beam statistics within the sampling noise (from runs of the same configuration on the reference). Report the runtime. For a bit-level comparison, a fixed-seed test case is needed.

## Site pitfalls met so far

- Jean-Zay: proxy only in login shells (remote commands run in `bash -l`); STORE not mounted on compute nodes; containers only from `$SINGULARITY_ALLOWED_DIR` via `idrcontmgr cp`, and only on compute nodes.
- CRIANN: no container runtime on login nodes (image copied from another site); login nodes interrupt multi-threaded processes.
- CC-IN2P3: jobs see all CPUs of the node; OpenMPI default binding put 8 OpenMP threads per rank on 1 or 2 cores (`mpirun --bind-to none`); MPI session files need `$TMPDIR` bound into the container.
- Containers under Slurm: `mpirun` inside the image must not use the Slurm launcher (`PRTE_MCA_plm=^slurm PRTE_MCA_ras=^slurm`): there is no `srun` inside.
- lxbatch (HTCondor): jobs run from a scratch copy of the executable, so the submit file starts `bash` in the clone; the scheduler mapping service is sometimes down (retry). The Kerberos ticket (`$KRB5CCNAME`) sits in the job scratch dir, which the container does not see: bind its directory, or EOS refuses writes from the image.
- MPI: an exception on one rank outside a `try` that calls `MPI.COMM_WORLD.Abort()` leaves the other ranks blocked until the wall clock. Guard the entry point.
- zsh does not split `$var` into words: pass job parameters as an array.
