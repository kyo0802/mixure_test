# Project organization implementation plan

Goal: make daily navigation follow the approved workflow, preserve scientific evidence and operational paths, consolidate old experiments physically.

Architecture: WORKSPACE contains human-readable links to authoritative originals. archive contains old experiment trees with hidden Windows directory junctions at their original names. src/scripts/tests/configs and active artifacts retain their canonical locations. No inference or scientific content changes.

- [x] Capture Git tracked status and hashes of all relocated files; record denied-access directories without changing ACLs.
- [x] Move historical output directories and accessible old temporary trees under archive using bounded native PowerShell Move-Item; create compatibility junctions; validate original paths and rollback on failures.
- [x] Compare Git tracked status before/after; preserve old root docs and exact bytes.
- [x] Build WORKSPACE/Pass_I, WORKSPACE/Pass_T and WORKSPACE/Data with named Windows shortcuts plus portable Markdown indexes; link authoritative reports rather than duplicate them.
- [x] Add START_HERE.md, workflow/current status, organization report, and a repeatable read-only link/hash checker. Hide legacy compatibility entries and runtime implementation details from normal Explorer view, recording reversible attribute changes.
- [x] Verify moved-file bytes, original-path reachability, shortcut targets, current imports and retained tracked state; report exact folder structure and limitations.

No stage advancement, prompt/dataset/annotation/model changes, commits, or push are part of this task. This directly executes the user's authorized cleanup inline. Previous frozen reports remain authoritative historical records; new navigation states the current status without rewriting them.

