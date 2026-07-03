# Agent Instructions

This repository is monitored by periodic PR review and merge agents.

Before reviewing, approving, or merging any pull request, the agent must verify that the author's intended implementation is actually present in the PR branch.

Required checks:

1. Inspect the current PR diff and changed files directly. Do not rely only on prior summaries, old review comments, or commit messages.
2. Confirm that the requested behavior is implemented in code, tests, and documentation where applicable.
3. If the PR claims to fix or add something, verify the concrete evidence in the repository with file paths and relevant lines.
4. If the implementation is missing, partial, stale, or reverted, do not approve or merge. Leave a review that states exactly what is not reflected.
5. When feasible, run the relevant tests or validation commands before merge. If they were not run, state that explicitly in the review.

Review and merge decisions must be based on the repository state that exists at the time of inspection, not on intent alone.
