# L2 integration audit: PRs #39–#50 onto main

## Why this integrator exists

PRs #39–#50 target stacked feature branches rather than `main`. Merging them individually closes the PRs but does not land their changes on the default branch. This dedicated PR is **based on current main (d2b12cdd097910cfee3eddf1de9454246a25d00d)** and is a single explicit review gate.

## Recovered features

| Source | Content |
| --- | --- |
| #39 AUTH-012 | Explicit, offline legacy-to-owner migration with backup and strict confirmation |
| #40 AUTH-013 | Session API, visible account name and explicit POST logout |
| #41 AUTH-014 | Cross-tenant GET/POST authorization regression tests |
| #42 AUTH-015 | Fail-closed public startup and operator release requirements in SERVICE.md |
| #43 AUTH-016 | Landing copy for local and later hosted auth modes |
| #44 AUTH-017 | Complete legacy copy verification and restore regression |
| #45 AUTH-018 | Parallel synthetic signed callback test; **superseded by #49** |
| #46 AUTH-019 | Cap concurrent pending OIDC states |
| #47 AUTH-020 | Cross-tenant import job HTTP tests |
| #48 AUTH-021 | Host-only session and login cookies (`__Host-`) |
| #49 AUTH-022 | Signed callback integration test from #45 adapted to main security chain |
| #50 AUTH-023 | Authentik Confidential Client secret at token endpoint, with PKCE |

## Deliberate conflict resolution

- **The current main `chatidy/db.py` is preserved:** it already includes #32's account-specific storage and #26's exclusion of non-text markers from content rules. The older stacked branch copy accidentally loses the #26 fix.
- **The current main `tests/test_search_index.py` is preserved** so the #26 regression stays active.
- **The current main `web/index.html` is preserved** for #27's ChatGPT/Claude import guidance; only the session account/logout panel from #40 is inserted. `web/style.css` stays the current main version.
- **#45 is not separately merged.** #49 carries the equivalent signed-token HTTP callback test.
- `README.md`, `ROADMAP.md`, `TASKS.md` and `aktuellerStand.md` remain on main without reverting existing changes; operational additions go in `SERVICE.md` and this audit. A later documentation consolidation can reconcile project-status claims.
- Previously integrated #25–#38 runtime and test changes on main remain in place. Newer changes from the #50 branch are brought over only where their content differs.

## Approval gates

1. **Do not merge before all latest-head Linux/Windows (Python 3.10/3.11/3.13) CI jobs and stdlib-only jobs pass.**
2. Owner reviews `main` target, changed files and any auth release limitations.
3. Before local smoke on real data, stop Chatidy and back up SQLite and import-job folders outside the repo. No automatic owner migration or enrollment.
4. After explicit merge approval, pull `main` with `git pull --ff-only origin main`, run `python -m chatidy` in the original local-only mode, and check landing, import help, chat data, search, jobs and tags.
5. **No public release or real Authentik credentials/data** before the operator checks in `SERVICE.md`: OIDC/confidential client, HTTPS/proxy, filesystem ACLs (especially Windows), backup/restore, owner-reviewed migration and account isolation.

All PRs and tests used synthetic data. No deployment, real personal data migration or merge to main is performed here.
