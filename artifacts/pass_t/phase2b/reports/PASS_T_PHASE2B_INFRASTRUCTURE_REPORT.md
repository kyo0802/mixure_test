# FindMind Pass T Phase 2b 基礎設施報告

Generated: 2026-10-13T17:16:50.442092+00:00

## 最終狀態

`PASS_T_PHASE2B_INFRASTRUCTURE_READY_AWAITING_MODEL_CONFIG`

真實 VLM 執行筆數：`0`。本次沒有上傳影像、沒有付費或雲端請求，也沒有下載模型。

## 已完成元件與路徑

- `src/memory_graph/pass_t/phase2b/authority.py`：唯讀 Phase 2a authority 與 hash 驗證。
- `eligibility.py`：逐視窗用途、品質限制與 metric 權限。
- `model_visible.py`、`inputs.py`、`builders.py`：opaque payload、私有 mapping、Video／Multi-image／Storyboard。
- `config.py`、`protocol.py`：模型能力、設定驗證、prospective protocol 與 freeze gate。
- `predictions.py`、`contracts/prediction_v1.json`：嚴格 raw parser、schema、citation 與 semantic guard。
- `backends.py`、`inference.py`：可註冊 backend、唯一 real-run 邊界、失敗也保存的 content-addressed run storage。
- `evaluation.py`：依 Phase 2a eligibility 限制輸出的 event-local evaluator。
- `scripts/run_pass_t_phase2b.py`：12 個 CLI 子命令。
- `PHASE2B_USAGE_ZH_TW.md` 與 `PHASE2B_DATA_EXPANSION_PLAN.md`：繁中操作說明與前瞻資料擴增計畫。

## 權威 DEV 狀態與逐視窗 eligibility

- Dataset SHA-256: `ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c`
- Frozen Phase 2a policy SHA-256: `c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4`
- 7 筆：2 筆 known-event matching、3 筆 strict-negative case alert、1 筆 descriptive uncertainty、1 筆 audit-only。
- test1 W03/W05、test2 W01、test5 W01：strict-negative case alert only。
- test5 W05、test7 W05：known PICKUP matching only；額外預測為 UNEVALUATED。
- test8 W07：descriptive uncertainty only。test3 W07：禁止 model run 與 scoring。
- 正式 benchmark eligibility 為 0，exhaustive positive 為 0，binding causality 仍是 `CAUSALITY_UNVERIFIED`。

## 剩餘品質限制

- test5 W05 and test7 W05 support conditional matching of their known PICKUP event only. Extra predictions remain UNEVALUATED.
- test1 W03/W05, test2 W01, and test5 W01 support case-level false-event alerts only; they do not establish a population false-positive rate.
- test8 W07 is descriptive uncertainty only.
- test3 W07 is excluded from model runs and scoring; original contamination exclusions remain binding.
- Accuracy, precision, recall, F1, hallucination rate, statistical significance, superiority, and generalization are undefined for this pilot.

## Representation、能力與 protocol 狀態

- 已支援 `REENCODED_AUTHORIZED_VIDEO`、`MULTI_IMAGE`、`STORYBOARD` builder。Video 以 FFV1/AVI 重編碼，保留私有 native PTS mapping 並報告 CFR distortion；不宣稱 native PTS 被保留。
- 真實模型能力：全部尚未驗證。mock 的 Multi-image／Storyboard 本機契約測試已通過，不代表真實模型可行性。
- Provider、backend、model、revision、限制、generation、budget、frame count、timing tolerance、repeat count 與 run order 仍未決。
- 最新 protocol 只有 `DRAFT_UNRESOLVED`；沒有 frozen Phase 2b protocol。`DECLARED` 不能作為 runtime verification。
- External data consent 預設 false；沒有 fallback 或 model substitution。

## Mock 與測試

- Mock suite: `True`; scenarios: `13`.
- Tests: `PASSED`; passed: `237`.
- Mock artifacts are isolated under `artifacts/pass_t/phase2b/mock/` and are explicitly marked non-experimental.

## 保護驗證

- Protected files checked: `16092`
- Changed protected files: `0`
- Git HEAD unchanged: `True`
- Git index empty: `True`
- 原有 tracked worktree diff 未改變: `True`

## Artifact SHA-256

- `artifacts/pass_t/phase2b/config/model_config.template.json`: `36fc9163786d162ae3d4579b7bdb1e044a94f1c76f1bdc3cca5ddf6309942a58`
- `artifacts/pass_t/phase2b/config/MODEL_CONFIGURATION_DECISION_SHEET.md`: `a338f67fde06d395205bf7643e90cf3a5740f0fbf90b1da0d0401803e998c2a0`
- `artifacts/pass_t/phase2b/config/protocol_decisions.template.json`: `69fa06e0f52039666f33338de3a9af060b6b7aece7f06a57851b822940eeea8e`
- `artifacts/pass_t/phase2b/mock/mock_suite.json`: `84273ed1191a678cf3288a87fb1cf9cf08132dacdd8afbef8b16a9696d241ce7`
- `artifacts/pass_t/phase2b/PHASE2B_DATA_EXPANSION_PLAN.md`: `1444a10c9d4e8c9e919bc3562896124227dca06ba2e3eb0afaf29697560a31b5`
- `artifacts/pass_t/phase2b/PHASE2B_USAGE_ZH_TW.md`: `902ffd9fc0e232c764102370a80581791d8b19c89e40de2cf9024668bf42cfce`
- `artifacts/pass_t/phase2b/readiness/eligibility.json`: `c231967ccc7007749e80f570d0abb33c65ee964a036f5da51fb2f60cbbd5c07b`
- `artifacts/pass_t/phase2b/readiness/GT_ELIGIBILITY_LIMITATIONS.md`: `5b1ad17c0398719d3c9a35762dadfe891a57b969f2a77b1e81d03112cf5322c5`
- `artifacts/pass_t/phase2b/reports/test_results.json`: `15885f9992188d30482085b52d5e7fa72bf420637ca9407c51acf8cb82542d9b`
- `artifacts/pass_t/phase2b/templates/event_reasoning_prompt_v1.txt`: `94b52f47e965691e01f85012ab0c8ad7653271c4fa229222ba190f2d6eabf679`
- `scripts/pass_t_phase2b_preflight.py`: `12bab312385119fac328650c8e9c52122f53f505aa03f1fccc79b519d7bdfdea`
- `scripts/run_pass_t_phase2b.py`: `4c419879d2b92e90204eede2f8cbb55888180005c363aeda2419d828b4bcfe50`
- `src/memory_graph/pass_t/phase2b/__init__.py`: `5b5808cac4f7278e0120f39295c43d2afadf40300e28741d064a0d5fc9f14a25`
- `src/memory_graph/pass_t/phase2b/authority.py`: `cc104596dacb1847433490163ac359ce4005aedd247f5cd9afeb107332961973`
- `src/memory_graph/pass_t/phase2b/backends.py`: `f432d1a1af70298f626494cc5fb5eac8012d2f29797aa2f68a04e0dd52f95381`
- `src/memory_graph/pass_t/phase2b/builders.py`: `447b5d826d465815dd927e6bb6f5e6d565c3b2da0701587b27a3df8a9d99e880`
- `src/memory_graph/pass_t/phase2b/common.py`: `4728823548401589a1a9ba061b09fb410e213156bf4f8f4d4714c8d2d772d79b`
- `src/memory_graph/pass_t/phase2b/config.py`: `64fae16245300fb52e51a1b1523fbd863004312b813b0e394b828b71954acea6`
- `src/memory_graph/pass_t/phase2b/contracts/model_config_v1.json`: `8b6bb917b9b039e72a9363916e742beb0cb57d9b2c3d33248c07b6a61d8eaac2`
- `src/memory_graph/pass_t/phase2b/contracts/model_visible_payload_v1.json`: `996fbd54f855c2ddcd42f77493f24b45e07bcab564cd215111858d6a51c5edda`
- `src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json`: `f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3`
- `src/memory_graph/pass_t/phase2b/eligibility.py`: `57b520e56d5bf3f8a9bba3cb67e52518f333937994b34679f78fcdb4a5254257`
- `src/memory_graph/pass_t/phase2b/evaluation.py`: `4d69a83f361579b0e22a00075b3e1e9a5255daec416c9a5937240f22c7f19826`
- `src/memory_graph/pass_t/phase2b/inference.py`: `e6bdbf19d4e3fb9a84a318fc49a88fc4b1f41e9af889fc8b80f30377793ba67f`
- `src/memory_graph/pass_t/phase2b/inputs.py`: `17e1bc14bfc05a944e13fb843b4d9ab4edd1fbcaab7ddd688f1de95c1cb5d021`
- `src/memory_graph/pass_t/phase2b/mocks.py`: `397afd2cf5d1bb4c5c1c4f1e7db1f60d1f647e26dc9b4ece2d83a6ae55d3aa39`
- `src/memory_graph/pass_t/phase2b/model_visible.py`: `c4707239d795167d2c054e1a23ef2c1e153ada3e34477e85939d4fa80c10889c`
- `src/memory_graph/pass_t/phase2b/predictions.py`: `c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37`
- `src/memory_graph/pass_t/phase2b/protocol.py`: `bc860e6f89401ff54dc27c6dc2dcc7b0e7c794f59d12c8bad5f918381cecee32`
- `src/memory_graph/pass_t/phase2b/reporting.py`: `31a1a44e466763d042f0e14d77312e9d99deef44ec52d6e4652e648d6a8862f9`

## 實際可用 CLI

完整 12 個命令與參數見 `artifacts/pass_t/phase2b/PHASE2B_USAGE_ZH_TW.md`。本次實際執行了 eligibility/readiness/config/capability/build/inspect/protocol/mock/report paths；freeze 在 unresolved gate 正確被拒絕。

## 下一步需要使用者決定

1. Fill `artifacts/pass_t/phase2b/config/model_config.template.json` as a new config file with one exact model/revision and verified capabilities.
2. Fill `artifacts/pass_t/phase2b/config/protocol_decisions.template.json` as a new decisions file, including GT-independent frame count, timing tolerance, repeat count, run order, and budget.
3. Validate capabilities and inspect the exact serialized payload before freezing the protocol.
4. Obtain explicit real-run authorization and data consent if the configured backend is external.

## 科學限制

This seven-window DEV set is exploratory, has no exhaustive positive windows, contains only known PICKUP positives, lacks PLACEMENT ground truth, has unverified binding causality and recording-session independence, and cannot support formal model accuracy or comparative claims.

Final status: `PASS_T_PHASE2B_INFRASTRUCTURE_READY_AWAITING_MODEL_CONFIG`
