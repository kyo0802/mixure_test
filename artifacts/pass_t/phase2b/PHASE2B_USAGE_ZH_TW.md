# Pass T Phase 2b 使用說明

## 目前狀態

目前只完成通用 VLM 事件推理基礎設施與 mock 驗證。尚未指定真實模型、凍結實驗 protocol 或執行真實推論。

## 環境

在 repository root 執行 PowerShell：

```powershell
$env:PYTHONPATH='src;artifacts/pass_i/runtime/vendor;outputs/current_development/video_event_experiment/.deps'
$py='.\.venv\Scripts\python.exe'
```

## 十二個 CLI 操作

```powershell
& $py scripts/run_pass_t_phase2b.py check-eligibility --output artifacts/pass_t/phase2b/readiness/eligibility.json
& $py scripts/run_pass_t_phase2b.py inspect-readiness
& $py scripts/run_pass_t_phase2b.py validate-config --config <model-config.json> --real-run
& $py scripts/run_pass_t_phase2b.py check-capabilities --config <model-config.json>
$env:PASS_T_PHASE2B_OPAQUE_SECRET='<至少 16 個字元的本機秘密值>'
& $py scripts/run_pass_t_phase2b.py build-inputs --config <model-config.json> --item-id <PT2A item id> --representations MULTI_IMAGE,STORYBOARD --frame-count <N> --storyboard-columns <N> --video-fps <FPS>
& $py scripts/run_pass_t_phase2b.py inspect-model-payload --package <input-package-folder>
& $py scripts/run_pass_t_phase2b.py prepare-protocol --config <model-config.json> --decisions <protocol-decisions.json>
& $py scripts/run_pass_t_phase2b.py freeze-protocol --draft <protocol-draft-folder>
& $py scripts/run_pass_t_phase2b.py run-mock-tests
& $py scripts/run_pass_t_phase2b.py run-pilot --protocol <frozen-protocol-folder> --input-package <folder> --confirm-exact RUN_PHASE2B_EXPLORATORY_PILOT --allow-real-run
& $py scripts/run_pass_t_phase2b.py evaluate-pilot --protocol <frozen-protocol-folder> --run <run-folder> --input-package <folder>
& $py scripts/run_pass_t_phase2b.py export-report --mock artifacts/pass_t/phase2b/mock/mock_suite.json --tests artifacts/pass_t/phase2b/reports/test_results.json
```

只有 `run-pilot` 可以呼叫真實 provider。它另外要求環境變數 `PASS_T_PHASE2B_REAL_RUN_PERMISSION=true`、完整 frozen protocol、完全一致的 item × representation inventory、預算、能力驗證，以及外部服務所需的明確資料分享同意。

`build-inputs` 只建立輸入，不會呼叫模型。`run-mock-tests` 只使用本機 mock backend。

## 模型設定步驟

1. 複製 `config/model_config.template.json`，填入唯一的 provider、backend、model、revision 與執行位置。
2. 對三種 representation 分別填入 `LOCALLY_VERIFIED`、`PROVIDER_VERIFIED` 或 `UNSUPPORTED`；`DECLARED` 不能通過真實執行 gate。
3. 填入模型的最大圖片數、單圖像素、context、temperature、sampling、seed、最大輸出、timeout、retry 與美元預算。
4. 若 media 將離開本機，必須把 `external_data_consent` 明確設為 `true`；預設為 `false`。
5. 複製 `config/protocol_decisions.template.json`，決定 frame count、video FPS、時間容差、重複次數、run order 與 pilot inventory。
6. 先跑 `validate-config`、`check-capabilities`、`build-inputs`、`inspect-model-payload`，確認安全後才準備與凍結 protocol。

## 評估限制

- test5 W05、test7 W05：只比對已知 PICKUP；未列出的預測事件保持 `UNEVALUATED`。
- test1 W03/W05、test2 W01、test5 W01：只報每個 case 是否出現 false-event alert，不計 population false-positive rate。
- test8 W07：只做描述性分析。
- test3 W07：不得執行模型或計分。
- 不產生 accuracy、precision、recall、F1、hallucination rate、顯著性、優越性或 generalization 宣稱。

## 憑證與敏感資料

設定檔、protocol、payload 與 log 不得存 API key、token、password 或其他 credential。使用 provider 核准的 secret 管理或環境變數。

