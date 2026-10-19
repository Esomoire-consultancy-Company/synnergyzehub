# Agent Run Controls

Rules for any agent run against the GitHub estate. Derived from the 19 October 2026 estate review and 321-call execution audit.

1. **Bounded scope.** Name the repositories or PRs in scope and set a tool-call budget before starting. No estate-wide failure sweeps.
2. **Reuse the inventory.** The 19 October estate review (202 repos, 824 PRs) is the baseline. Do not rebuild it without a stated reason.
3. **Persist findings as produced.** Append each finding to a tracking file or issue immediately, so a usage limit or interruption does not discard progress. A new run starts from the last recorded state.
4. **No redundant evidence.** Do not re-fetch unchanged data or re-poll statuses whose head SHA has not changed.
5. **Evidence per repair.** Each proposed repair reports the commit SHA, the checks run and their results.
6. **Respect dependencies.** Review and promote stacked PRs parent-first. A green child does not resolve a failing or conflicting parent.
7. **One canonical PR per problem.** Before opening a repair, check for existing overlapping PRs and extend or supersede them.
8. **Skip known non-defects.** See `estate-triage.md`.
