# Fast GT consolidation implementation plan

Goal: Validate two original reviewer submissions, prepare compact owner CSV adjudication, then reuse all existing three-model outputs without inference.

Architecture: Add a small standard-library CLI around the existing annotation contract and temporal matcher. Human alignment is independent of predictions. A separate prediction-review table resolves physical identity/event equivalence; no automatic promotion or overlap-only merging. Coverage is explicit and can be scoped to partial source-time intervals.

User requests immediate inline execution, no new website, no historical edits, no commit/push. Work in the current repository.

- [x] Validated both submissions, nine original hashes, 1,712 native-PTS references and 552 execution receipts; preserved source bytes and 2,235 input hashes.
- [x] Implemented consolidate_findmind_gt.py; generated 34 owner groups, 41 prospective coverage scopes and immutable provenance. Finalization is gated on actual owner decisions.
- [x] Implemented evaluate_consolidated_vlm.py with existing tolerances/matcher, separate candidate/strict views, explicit identity/event grouping and invalid/unknown exclusions.
- [x] 21 CPU tests pass. Initial Windows temp ACL failure documented; isolated project test directory works.
- [x] Ran alignment and descriptive evaluation; report and instructions published in WORKSPACE/VLMtest. Stopped at human decisions, not additional planning.
