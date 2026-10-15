# Qwen NF4 輸出稽核保存與測試報告

日期：2026-10-15。完整數值與來源列表見 `preservation.json`、`protected_before.json`、`source_authority.json`、`test_results.json`。

## 完整性結果

- 搬移後實際專案根目錄為 `C:/Users/smile/Desktop/test2/mixure_test_SAM`；此次所有新寫入都在 `artifacts/pass_t/phase2b/output_failure_audit/qwen_nf4/20261015/`。
- 參照既有 protected inventory，補入目前 source/scripts/configs/tests 與兩輪 capacity 檔案，建立本次開始時的獨立 baseline。結束時核對 **29,716 個既有檔案，變更／遺失 0**。開始時既有缺檔 0。
- 6 個 checkpoint／權重二進位檔刻意不讀取，不載入模型；確切排除路徑記在 preservation.json。沿用原資產回條與 revision metadata，不聲稱本次重新驗證權重 tensors 或官方 checksum。
- Git HEAD 保持 `149c70a21b51160e4316a9334758417d057aee80`；index、tracked diff、staged diff、tracked status 的 SHA 均與本次開始時一致。既有大量刪除狀態保留；本次無 stage、commit、push。
- 最後 capacity 的原 completion receipt 覆蓋 422 檔，全部驗證成功；較早輪次也按自己的原 receipt 驗證成功。capacity_results.json 的原回條與實際 SHA 相同：`7d8fed22e866609b30b85f7f4d34b3beffdf46e98220dd435a0450391d6fc712`。
- 兩輪 **66 個 generation attempts** 均找回原 raw、iteration/resource、transport receipt。以原 resource 欄位與原 raw SHA、耗時匹配，沒有因相同回答文字而合併不同 attempt。PRIMARY 固定 33；ENGINEERING_HISTORY 另 33，CSV 不隱藏分组。
- 原 Prediction V1 schema 和 validator 與歷史 protected SHA 相同，CPU replay **66/66 與完整歷史 validation object 一致**。primary 15/33 pass 與 18 failures 均保留。
- Phase 2a 原 DEV export、複核 sidecar、已批准 policy SHA 均符合權威來源；只核對 authority／格式及既有用途，未用 GT 事件時間選 frame、調參或選 favorable 輸出。原 GT、人工答案與契約均未改寫。

## CPU-only 測試

命令：

```powershell
.venv/Scripts/python.exe -X utf8 -B artifacts/pass_t/phase2b/output_failure_audit/qwen_nf4/20261015/test_audit.py
```

**28 passed，0 failed，0 errors，0 skipped**。逐項輸出保存於 `test_log.txt`。測試包括 attempt ID、去重、33/33 分輪、warmup/measured、缺 receipt／錯 hash、歷史 pass/replay、multi-label 與 secondary errors、JSON path、empty/null/missing、EOS 非推測、cap/timeout、unsupported/unconsumed aliases、malformed event count、複雜度、原 raw 不變，以及禁用模型／Graph／protocol 模組。

每個稽核與測試子程序最先設定 `CUDA_VISIBLE_DEVICES=''` 並安裝 fail-closed import guard；torch、transformers、bitsandbytes、accelerate、cv2、av、local VLM backend 等禁止匯入。只有 stdlib、既有 jsonschema 與 prediction/common CPU 模組被使用，沒有先建立 GPU runtime 才宣稱沒呼叫 generate。禁用模型模組的負向測試確實觸發 ImportError。没有執行 broad regression 或 processor/model load。

所有 test dictionaries 是 CPU 契約 fixture，不是新 model prediction；臨時 test files 只在新的 audit namespace 建立並結束清理。未測得視覺正確性或新的模型能力。

## 稽核程式修正紀錄

第一版 audit matcher 把 adapter 在 transport 存檔後加入的 `citation_allowed_aliases` 也拿來作原 resource 全字典比較，因此報 transport 匹配不到。該中間分析保存在 `diagnostic_initial/`，沒有覆寫原輸出。修正為只排除這個有程式來源證據的後加欄位，核對它與 processed aliases 相同，再精確比較其他 resource 欄位及 raw hash；最終 issues 清單為空。不是替換 attempt、修補模型 JSON 或放寬 validator。

中斷恢復時檢查 analysis、CSV、八份已生成報告和 test_results 都完整，沒有生成到一半的程式需重跑；隨後實際執行尚缺的完整 closeout hash 核對，再新增本報告與 audit 封存回條。

## 本次未觸發的研究行為

新 GPU／VLM calls **0**，實際 Phase 2a pilot count 保持 **0**，新 model predictions **0**，原 outputs/receipts 修改 **0**，policy/schema/parser/runtime/prompt 修改 **0**，GT 修改 **0**，Memory Graph writes **0**，protocol freeze **0**，Git commit/push **0**，下載／安裝／外部付費推論 **0**。

`audit_completion_receipt.json` 只記錄本次稽核交付的 hash、測試與保存結果，不是 protocol freeze receipt，也不記錄或推定 human approval。
