# Blockers and Non-Claims

1. `scripts/bin/harness-cli` and the entire `scripts/bin` directory are absent
   at the pinned starting revision. Matrix, tool discovery, intake, story
   verification, trace, audit, intervention-row, and proposal commands all
   remain unavailable; observed attempts exited 127.
2. Full `npm test -- --run` exits 1 because `better-sqlite3` has no native
   binding after pre-lock `npm ci --ignore-scripts`. Rebuilding after the final
   lock was not allowed; 27 product tests were skipped by the failed suite.
3. P6 completed after the five-minute fresh-agent window. Its late discovery,
   repair, and passing proof are preserved, but the card outcome is failed.
4. No external trusted-owner registry bytes, independently pinned registry
   digest, public key, signature, or signing authority were supplied to the
   operator. No key was generated and no artifact was signed.
5. Because authentication is absent, this directory is real local baseline
   evidence but not an authenticated publication packet. No candidate/Phase 6
   disclosure was performed or timestamped by this operator.
6. The runtime exposed no authoritative token telemetry, so token usage is
   recorded as unavailable rather than estimated.
7. No push, deployment, remote mutation, remote fetch, or other checkout
   mutation was performed.
