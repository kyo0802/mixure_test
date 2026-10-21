# Phase 9 implementation checklist

Goal: extend the existing local Streamlit Demo with a persistent, user-triggered departure assistant, explicit packing confirmations and a working handoff into the existing Graph search/evidence UI.

- [x] Add checklist_store.py: atomic JSON, OS file lock, configurable essentials, immutable per-check item snapshots, per-memory active check, explicit confirm/undo events and idempotent actions.
- [x] Add departure.py: evidence retrieval through the current search Agent, independent packing/evidence statuses, deterministic reminders, typed search handoff.
- [x] Extend the current application with Home / Departure / Search navigation. Preserve memory selection, existing upload/jobs, evidence and timeline. Reset only by creating a new departure check.
- [x] Focused store, integration and Streamlit tests, existing regressions and real browser competition flow on the saved test8 session. No GPU rerun.
- [x] Publish the actual report and concise demo guide under WORKSPACE/VLMtest and artifacts/phase9. No commit/push.

Validated: 15 Phase 9 + 15 Demo + 71 existing tests; actual browser Home -> departure -> phone search -> return -> confirm/undo -> all complete -> reset -> review history -> real service restart -> resume unconfirmed check -> keys UNKNOWN. All browser packing events tagged DEMO_PRESENTATION, not physical possession.

Checklist configuration changes apply to the next check; current and historical checks retain their own item snapshots. Switching memory sessions selects that memory's check, never transfers packing confirmations.
