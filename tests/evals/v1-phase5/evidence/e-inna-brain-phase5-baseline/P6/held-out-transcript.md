# P6 Held-Out Fresh-Agent Timeout Transcript

Packet-normalization annotation (added after the source run): this
authenticated requirement artifact is bound to the verifier-canonical packet
environment digest
`1a2c1145670897c3d85a0fb9509704f3b70174a38fd0a6ae69e38d0b9f3c1f15`.
The source-run legacy digest was
`1808dd68477e80c0fdb5bb04b4f1e99b280886432046022deb85772494af8256`,
computed with a trailing newline. The original timeout transcript and failed
outcome are unchanged.

## Comparable Held-Out Seed

The durable capability was committed at `2026-07-18T07:07:28Z` in
`7c10ab56b69eec14107b68ede6fdb722c2248871`. A distinct held-out seed was then
created at `2026-07-18T07:07:53Z`:

- Path: `src/infrastructure/phase5-pilot-heldout-dynamic-seed.ts`
- Direction: infrastructure to interfaces
- SHA-256: `100646aadf5961124c636f5270bbca32d7f74b559973511d87d59d9531ec9e51`

The fresh agent received only the repository, `AGENTS.md`, and the neutral
`held-out-prompt.md`. It was explicitly barred from the original discussion,
rehearsal, repeated-correction evidence, and capability diff. No checker name,
acceptance command, diagnostic, repair, or hidden evidence was relayed.

## Timeout And Negative Result

At `2026-07-18T07:13:06Z`, after the human/orchestrator observed the five-minute
limit had been reached, the agent was interrupted. The orchestration API
reported its previous status as `running`.

At interruption, the held-out seed was absent, but the agent had produced no
`held-out-transcript.md`, no ordered command record, no discovery path, no
environment comparison, and no final acceptance exit code. Therefore seed
absence cannot be converted into proof that the fresh agent discovered and
used the inherited capability. No evaluator reconstruction was supplied.

Outcome: `failed`.

At `2026-07-18T07:13:28Z`, the operator confirmed the seed remained absent and
ran `pnpm test:architecture` only as cleanup safety validation; it returned exit
0. That evaluator check proves the worktree is safe, not that the fresh agent
met P6 inheritance acceptance.
