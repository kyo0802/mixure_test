# FindMind project instructions

## Report placement and daily navigation

The user's current workflow is Freeze → model selection → Stage 0 Smoke → Pass I/T parallel annotation and implementation → Qwen baseline comparison → Shadow mode → End-to-end → Memory Graph. Current stage: Pass I/T parallel annotation and implementation. Update progress from actual evidence, not this snapshot alone.

Whenever a task completes a report, publish a readable copy of its latest main report in the matching WORKSPACE folder before handing it off:

- Pass T: `WORKSPACE/Pass_T/LATEST_REPORT.md`.
- Pass I: `WORKSPACE/Pass_I/LATEST_REPORT.md`.
- VLM model integration, inference, ablation and comparison experiments: `WORKSPACE/VLMtest/LATEST_REPORT.md`. Use this destination even when historical raw artifacts remain under `artifacts/pass_t/`; Pass T annotation/contracts belong in Pass_T. This is the user's report-placement instruction from 2026-10-18.
- Other workflows: use their corresponding WORKSPACE folder, following the existing naming style.

Update that folder's README so the latest report and current decisions are immediately visible. In the final response, link to the WORKSPACE copy first. Do not require the user to navigate version-number or hash directories to find the latest report.

Keep immutable authoritative reports, evidence and receipts in their original artifact namespace. The WORKSPACE copy must identify its source and update date. Resolve relative links from the WORKSPACE location so they remain usable. Do not edit a frozen report to update navigation.

Reuse the fixed latest-report filename; do not create another version directory or shortcut for every progress update. Clearly label older links as historical and update existing current decision/tool shortcuts when their targets change.

Honor any task-specific publication restrictions or narrower writable scope; if they prevent updating WORKSPACE, report that conflict explicitly instead of silently omitting the daily entry.

All project work remains inside mixure_test_SAM unless the user explicitly expands scope. Preserve unrelated changes, datasets, annotations and frozen evidence. Use the session's Context Mode instructions for large data and logs.
