# L2 recovery: closed stacked PRs #30–#38 into main

## Why this PR exists

PRs #30, #31, #32 and #35–#38 were merged into their feature-branch bases rather than `main`. GitHub therefore reported `merged`, but the code was not integrated into the default branch. PRs #33 and #34 were already merged into `main` and must not be applied twice.

## Integration method

This is a fresh integration branch **based on `main`** after #25–#29, #33 and #34. Only the relevant Python runtime files and synthetic tests were carried over from the #38 branch. Existing `main` web assets, import-help UI, import handling and docs from #26/#27 were retained instead of overwritten by older versions.

Relevant original PRs: #30 identity lookup, #31 enrollment, #32 account DB and jobs, #35 session/challenge state, #36 HTTP session protection, #37 OIDC token/code exchange, #38 login/callback/logout. #25, #33 and #34 are already integrated on `main`.

## Important release limits

- **Do not deploy publicly.** This is integration of previously prepared code, not a live Authentik or reverse-proxy security acceptance.
- `CHATIDY_AUTH_REQUIRED` remains opt-in and the legacy local mode remains supported.
- No accounts or existing chats are automatically assigned or migrated.
- The next stacked PR (#39, migration) and further PRs (#40–#50) must be reviewed and retargeted to `main` or a properly rooted integration branch before merging; do not merge them into closed feature branches.
- Review CI on Linux and Windows and run a local smoke test with a **backup** before merging. Real Authentik/HTTPS, Windows ACLs and owner-approved migration remain separate gates.
