# Repository delivery rules

- Follow `docs/SD-ARCH-3.0.md` as the authoritative architecture and `docs/SIMPLE-BOARD.md` for current package status.
- Use the existing STK ticket IDs and corresponding D3 package name in branch, commit and PR descriptions. Do not invent tracker IDs.
- Never push directly to `main`. Create a ticket-named branch, commit only related changes, push the branch and open a PR for owner review.
- Do not merge PRs or enable automatic merging. Provide the PR link, validation and blockers, then wait for the owner to review, merge and confirm the next package.
- Preserve unrelated tracked and untracked WIP. Do not stage it with the current task. Do not modify historical evaluation fixtures.
- Keep the progress board lightweight: one Markdown file, updated at meaningful package milestones. Preserve historical evidence without treating synthetic acceptance as real-market readiness.
- No paid APIs, purchases, external deployment or broker orders without explicit authorization. Do not reopen the approved hosting selection.
