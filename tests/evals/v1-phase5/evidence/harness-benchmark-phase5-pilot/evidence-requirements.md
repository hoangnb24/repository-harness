# Exact P0-P7 Evidence Requirement Map

The requirement text below is copied verbatim from Phase 5 card revision 1.

| Card | Outcome | Exact evidence requirement | Artifact |
| --- | --- | --- | --- |
| P0 | passed | Exact subject identity and command transcript. | `cards/P0/evidence.md` |
| P0 | passed | Path mapping and target-owned before/after SHA-256 report. | `cards/P0/evidence.md` |
| P0 | passed | Manifest, status, and audit outputs with exit codes. | `cards/P0/evidence.md` |
| P1 | inapplicable | Eligibility finding for P1. | `cards/P1/eligibility-finding.md` |
| P1 | inapplicable | Source before/after digests and archive/export/receipt identities when eligible. | `cards/P1/eligibility-finding.md` |
| P1 | inapplicable | Kill-point transcript or signed inapplicability finding. | `cards/P1/eligibility-finding.md`; signing remains an orchestrator blocker |
| P2 | passed | Prompt and ordered command transcript with exit codes. | `cards/P2/evidence.md` |
| P2 | passed | Core-command count computed from the transcript. | `cards/P2/evidence.md` |
| P2 | passed | Target-native acceptance output and changed-path list. | `cards/P2/evidence.md` |
| P3 | passed | Fixed interruption point and both agent transcripts. | `cards/P3/durable-plan.md`, `cards/P3/resume-transcript.md` |
| P3 | passed | Durable plan before and after resumption. | `cards/P3/durable-plan.md` |
| P3 | passed | Environment digest and final target-native proof. | `cards/P3/resume-transcript.md` |
| P4 | passed | Seed digest and failing output. | `cards/P4/evidence.md` |
| P4 | passed | Repair diff and passing output from the identical command. | `cards/P4/evidence.md` |
| P4 | passed | Intervention events including any correction relay. | `cards/P4/evidence.md`, `interventions.json` |
| P5 | passed | Clean revision and seed identity. | `cards/P5/evidence.md` |
| P5 | passed | Feedback commands or captured target-owned feedback with timestamps. | `cards/P5/evidence.md` |
| P5 | passed | Final acceptance output and intervention log. | `cards/P5/evidence.md`, `interventions.json` |
| P6 | failed | Repeated-correction evidence and durable capability diff. | `cards/P6/evidence.md`, `benchmark/orchestrator/test/phase5-capability-inheritance.test.ts` |
| P6 | failed | Held-out prompt and fresh-agent transcript. | `cards/P6/evidence.md`, `cards/P6/held-out-transcript.md` |
| P6 | failed | Discovery path, environment digest, and target acceptance output. | `cards/P6/held-out-transcript.md`; late completion is preserved as timeout-negative |
| P7 | passed | Bounded scope, trigger, and two run transcripts. | `cards/P7/evidence.md` |
| P7 | passed | Before/after path and digest inventories for both runs. | `cards/P7/evidence.md` |
| P7 | passed | Target validation and gardening-review interventions. | `cards/P7/evidence.md`, `interventions.json` |

P1's card asks for a signed inapplicability finding, but the user explicitly
prohibited signing and stated that authentication belongs to the orchestrator.
The unsigned concrete finding is preserved; authenticated publication remains
blocked rather than fabricated.
