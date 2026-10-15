# CPU output audit implementation plan

Goal: audit unchanged historical outputs and prepare prospective decisions, with no model execution or protocol changes.

Architecture: one attempt per row; final 33 primary, first 33 separate history. Reuse only the CPU strict prediction module after source/hash verification. Independently inspect errors that its structural early return suppresses, without editing predictions or changing historical pass counts. All new writes stay in this namespace.

- Capture HEAD/index/worktree and current protected hashes; verify original completion receipts and capacity_results.
- Recover attempt receipts, raw output copies and transport receipts; verify unique identity, hashes, prompt/schema versions, aliases, EOS and settings.
- Reproduce historical strict validation, extract complexity features and all independently demonstrable secondary errors.
- Test CPU-only logic with forbidden imports failing closed, including malformed/missing inputs and no double counting.
- Produce all nine requested reports/tables, a prospective 24-row decision table and fixed limited regression design; explicitly assess matching and target semantics.
- Compare source/evidence and Git state, seal a separate audit completion receipt. Stop awaiting human decisions.

No inference, model imports, original edits, schema/prompt repair, freeze, Graph writes, commit or push. New namespace chosen as one readable date rather than a second public navigation hierarchy.
