# Read-only preservation report

Result: **PASS**.

Scope: 201 relevant existing files, including all authoritative V1D namespace files and 73 synthetic media assets, selected V1C/V2/diagnostics, phase2b Python/JSON sources and existing WORKSPACE navigation. Full per-file before/after SHA maps: preservation_before.json / preservation_after.json. Only this one new directory was written. No existing files made writable or restored. This diagnostic did not access real Phase 2a DEV media/GT, initialize a model/CUDA, run generation, create fixtures, freeze, run pilot, write Memory Graph, commit or push.

## Git

| Item | Before | After | Equal |
| --- | --- | --- | --- |
| head | 149c70a21b51160e4316a9334758417d057aee80 | 149c70a21b51160e4316a9334758417d057aee80 | True |
| index_sha256 | dffc3d8be09510539408259520670dca17005963bfbe802fd9c65b24ae6eafe4 | dffc3d8be09510539408259520670dca17005963bfbe802fd9c65b24ae6eafe4 | True |
| staged_diff_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | True |
| worktree_diff_sha256 | 93055a4bbce6010e0c1aa2490079ab8c79aa59f37bdfd61cecdc15a988ba6c9a | 93055a4bbce6010e0c1aa2490079ab8c79aa59f37bdfd61cecdc15a988ba6c9a | True |
| existing_status_sha256 | 1fcf3903d39b420212f68736b1c674a021471ccc67624c520b567f80f7065f86 | 1fcf3903d39b420212f68736b1c674a021471ccc67624c520b567f80f7065f86 | True |
| existing_status_lines | 53287 | 53287 | True |


Git status excludes this newly authorized directory when comparing existing state. Original accessible status lines: 53287. Existing staged/unstaged/untracked changes were preserved, not cleaned/reset. GIT_OPTIONAL_LOCKS=0, no git write commands. Git status had permission-denied/long-path inventory warnings and diff had line-ending warnings; coverage of inaccessible paths is not claimed. Direct file hashes supplement Git's normalized diffs.

## Protected artifacts

| Protected set | Verification |
| --- | --- |
| V1C task prompt | 3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722 |
| V1D task prompt | 7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0 |
| Prediction V1 schema | f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3 |
| Parser and authoritative Validator (predictions.py) | c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37 |
| V2 formatting | 9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e |
| Video Array Bridge | 5cfebb8d93294585cc62531258fba79f2d5abc2cb57e0f1ba1e108664288ed4e |
| NF4 runtime | fc15d9012a3a992e4dcb9e66a3b458b242c319b1efe5f4d30dae19b81364547b |
| Eight raw outputs | All 8 direct hashes unchanged; completed receipt chains verified |
| Synthetic fixture media | All 73 direct byte hashes unchanged; only C04 eight source images decoded |
| All relevant existing inputs | 201 compared; changed=0; unexpected additions=0 |
| Existing WORKSPACE latest/README/decisions/results | Unchanged under narrower user write scope |
| Locked diagnosis criteria | a7846cfbb52086ab5ab933cd1a6a223b78d140bbe8940445486e8e9bed05a08b |


## Execution scope and limitations

The CPU script guards writes outside this new directory, blocks imports of torch/transformers/tensorflow/huggingface_hub, model paths/weight reads, real-data roots and sockets, and allows only read-only Git subprocesses. analysis_execution_receipt.json records imports and access counters. No tokenizer or processor was instantiated; PIL decoded only existing C04 source RGB. Other image reads were SHA byte reads only. No network/download/install was used. Diagnostic script corrections inside this new directory are recorded separately; locked criteria stayed immutable.

No known real DEV content access was made by this diagnostic. Git read metadata/diff/status; it did not open DEV media/GT for analysis. Byte hashes and Python audit controls do not prove what unrelated external processes did, nor provide a machine-wide native access trace. Model asset binaries were not read or rehashed in this CPU task. New report files are deliberately outside the old authoritative frozen namespace; old manifests/reports remain unchanged.
