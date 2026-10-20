# FindMind：VideoLLaMA3 全部可用視窗推論報告

更新：2026-10-17。狀態：**VIDEOLLAMA3_AVAILABLE_WINDOW_INFERENCE_COMPLETE**。

## 1. 結論與完成範圍

已完成官方 VideoLLaMA3-7B 整合、下載、實際生成及資料集分析。**16／16 個不同輸入均已生成，涵蓋 17 個可用視窗條目；執行失敗 0、重試 0。** test1 W03/W05 的輸入完全相同，後者明確指向前者的結果，沒有另跑或當成獨立樣本。

**工程可執行，但本次物理觀察品質不足，不建議取代 Qwen，也不建議現在加入雙模型主流程。** 16 份輸出只有 2 份 full strict-valid；已知的 test5/test7 手機 PICKUP 均未得到可用的手機事件假說。這是目前固定配置的 DEV 結果，不能推論 VideoLLaMA 整個模型家族的能力上限。

「全部可用視窗完成」不等於「每支影片都完成推論」：共發現 69 個現有條目，52 個沒有既有視覺影格配置，因此不自行補採樣。test6 的 6 個條目全屬此類，沒有 test6 模型結果。完整逐筆原因在 [dataset_inventory.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/dataset_inventory.json)。

## 2. 資料與輸入完整性

- 來源為現有 `event_windows/event_manifest.json` 的 69 筆，已核對既有 builder freeze。9 支原始影片的 SHA-256 全部與 development_inputs 一致。
- 使用既有 Uniform8 的視窗有 7 個條目、6 個不同輸入；另外 10 個視窗保留原有 7–27 張密集影格配置。沒有按結果選容易案例或重新設計採樣。
- Uniform8 直接讀取並核對既有乾淨 PNG。密集配置的舊 PNG 帶有標記，因此從雜湊相符的原影片解碼**相同 frame index**，保存乾淨副本與原生 PTS，不使用鄰近影格替代。新副本及被標記原圖的 path/hash 都在清單中。
- 保留既有 Uniform8 aliases；密集配置原本沒有 model alias，新增可追溯的 `F{index-start+1}`，同時保存實際 source index。這是編號，不是重新採樣。
- 僅輸入影格、alias、通用 system/task/schema。未輸入 GT、人工答案、target ID、追蹤／Re-ID／QC／Identity Guard 資料。沒有 target reference，沒有將物件綁為 phone_01。
- 重疊關係逐筆保存；test3 W02/W03/W07、test4 W06/W08、test8 W06/W07 等不能當作獨立樣本。錄影 session 的獨立性仍未證明。
- 這些影片已參與專案開發，屬 DEV；沒有使用 val_set 或宣稱 untouched held-out benchmark。

## 3. 實際模型與執行配置

| 項目 | 實際值 |
|---|---|
| 官方模型 | [DAMO-NLP-SG/VideoLLaMA3-7B](https://huggingface.co/DAMO-NLP-SG/VideoLLaMA3-7B) |
| 固定 revision | `d5b763e368861e7f5096e7ff1b49f92fbccf8ae6` |
| 實作 | 該 revision 的官方 custom code，local-only 載入；官方 SDPA 路徑 |
| 模型路徑 | `C:/Users/smile/Desktop/test2/mixure_test_SAM/.models/VideoLLaMA3-7B` |
| 相依隔離 | `.runtime/videollama3/vendor`：Transformers 4.46.3、tokenizers 0.20.3、decord 0.6.0；保留現有 Qwen 套件 |
| Torch／量化 | Torch 2.10.0+cu128、bitsandbytes 0.50.2；語言層 NF4 double quant，BF16 compute |
| 實際量化檢查 | 196 個 Linear4bit 模組；vision encoder/projector 未量化，vision 參數全部 BF16 |
| 視覺輸入 | 依時間排序的獨立圖片；沒有宣稱 native-video temporal attention |
| 視覺預算 | 官方 processor 全批合計 max_tokens=4096、min_tokens=16、merge=1；實際 3780–4032 visual tokens |
| Uniform8 實際尺寸 | 每張 420×224、grid=[1,16,30]；8 張共 3840 visual tokens |
| 生成 | greedy、seed 42、max_new_tokens 1024、300 秒停止條件；無品質重試 |
| 載入時間 | 28.55 秒（不含下載、輸入驗證與前置 imports） |
| 16 次生成合計 | 176.03 秒；逐窗處理合計 181.10 秒（非整項任務 wall time） |
| GPU 高峰 | Torch peak allocated 8.39 GiB、reserved 8.49 GiB；不是整張 GPU 含其他程式的總峰值 |
| 結束狀態 | 14 次 EOS；2 次 token cap；timeout 0、OOM 0、執行失敗 0 |

載入前檢查可用 VRAM/RAM，逐窗再檢查；這不是持續監控的全系統資源保證。模型 generation config 原帶 temperature/top_p/top_k，因此 Transformers 顯示 greedy 下忽略這些 sampling 參數的警告；實際 `do_sample=False`，沒有切換成隨機取樣。

Hugging Face 固定模型 metadata 標示 Apache-2.0；另官方專案對研究／非商業用途有使用聲明。權重與程式的來源及授權資訊已保留，這份報告不提供概括商用授權結論。參考 [官方程式庫](https://github.com/DAMO-NLP-SG/VideoLLaMA3)。

## 4. 每支影片與逐窗結果

下表的 strict 與描述統計以**實際不同輸入**計算；成功條目包含明確的 duplicate reuse。未通過合約不等於執行失敗。

| 影片 | 發現 | 可用／成功條目 | 實際生成 | 無配置 | full strict | 主要描述結果 |
|---|---:|---:|---:|---:|---:|---|
| test1 | 9 | 3／3 | 2 | 6 | 0／2 | W01/W03 只寫 basketball；W05 共用 W03 |
| test2 | 8 | 2／2 | 2 | 6 | 1／2 | W01 寫 ball/phone/snack ON_SURFACE；W08 把手中手機描述為 brush |
| test3 | 9 | 3／3 | 3 | 6 | 0／3 | W02 寫 ball/box，另有空 citations；W03/W07 只寫 ball |
| test4 | 8 | 2／2 | 2 | 6 | 0／2 | W06/W08 只寫 ball，缺 uncertainty |
| test5 | 8 | 2／2 | 2 | 6 | 0／2 | W01 引用不存在 aliases；W05 連列 aliases 至截斷 |
| test6 | 6 | 0／0 | 0 | 6 | 不適用 | 沒有既有 frame configuration，未執行 |
| test7 | 7 | 1／1 | 1 | 6 | 0／1 | W05 只寫 ball，漏掉已知手機拿起 |
| test8 | 9 | 3／3 | 3 | 6 | 1／3 | W04 寫 ball；W06 截斷；W07 observations=[] |
| test9 | 5 | 1／1 | 1 | 4 | 0／1 | W03 寫 hand HELD_BY_PERSON，但 JSON 括號錯誤 |
| 合計 | **69** | **17／17** | **16** | **52** | **2／16** | 無有效事件候選 |

13 份可解析原文的 status 全為 NO_CONFIRMED_EVENT，EVENTS/UNCERTAIN 各 0。另 3 份無法解析，**沒有把它們算成 NO_EVENT**。無觀察、未觀察到指定目標、沒有生成事件，以及人工確認無事件，是不同事情。

### 結構、引用與原文

- Raw JSON syntax：13／16；完整 schema/semantic/citation strict：2／16（test2 W01、test8 W07）。
- 10 份缺必填 `uncertainty`；test3 W02 的兩組 states 使用空 `frames`。沒有補欄位、刪空項或弱化 schema。
- test5 W05、test8 W06 各生成 1024 tokens，連續列舉 aliases 後截斷；test9 W03 在 EOS 結束，但括號位置錯誤。三者保留原文，不修 JSON。
- test5 W01 的已解析內容引用 7 個未供應 aliases；這是額外診斷，即使 schema 已先失敗仍會報告。其餘 12 份可解析內容沒有未知 alias，但**alias 存在並不代表影像支持該狀態**。
- 本模型 16 份原文皆沒有外層 Markdown fence，因此 fence extraction 沒有改善本次結果。歷史 Qwen 使用相同的「單一完整外層 fence」提取政策，另列 descriptive 結果；不提升為 authoritative prediction。
- 原文在每個 `calls/<window>/raw.txt` 立即保存；input_receipt 記錄來源、PTS、grid、tensor hashes，generation 記錄 token IDs、EOS/cap、時間與資源。`ledger.jsonl` 支持續跑；完成結果不再生成。

## 5. 與既有 GT／人工證據的對照

以下使用既有 Phase 2a DEV 匯出及 exhaustiveness sidecar；**沒有新增人類標註**。本次看到 contact sheets 的判斷屬助理視覺分析，不能稱為 human-adjudicated GT。原始評估來源的 formal_eligible 仍為 0。

逐窗八面向助理分析與 GT 來源 hashes 另外保存在 [physical_evidence_analysis.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/physical_evidence_analysis.json)。自動 parser summary 的初始 UNREVIEWED 標記不會被改寫為人工 adjudication。

| 可用參照 | 本次輸出 | 可支持的結論 |
|---|---|---|
| test1 W03/W05：同一個 strict-negative unit | 只寫 ball；缺 uncertainty | 非結構化文字沒有事件，但不能當有效 structured negative；手機觀察缺失 |
| test2 W01：strict-negative | ball/phone/snack 都寫 ON_SURFACE，strict-valid | 所選 8 格與桌面狀態相容；是唯一有手機觀察的 parsed 結果，不證明 global identity 或全窗評估能力 |
| test5 W01：strict-negative | 只寫 ball，引用未供 aliases，strict-invalid | 不能拿來增加正確負例數 |
| test5 W05：非完整 known PICKUP | 截斷 JSON，沒有可用手機狀態／事件 | F0001/F0016/F0032 手機在桌面，F0062/F0077 可見手持；本次未提供可用 hypothesis，並非有效的 NO_EVENT 預測 |
| test7 W05：非完整 known PICKUP | 只寫 ball，缺 uncertainty | F0001/F0016 桌面、F0031/F0046 手持的可見變化沒有被描述；沒有可用手機 PICKUP hypothesis |
| test8 W07：INSUFFICIENT_EVIDENCE | strict-valid NO_CONFIRMED_EVENT、observations=[] | 空結果不能把 GT uncertainty 改成已確認負例，也不能證明適當 abstention |

test3 W07 的 GT 繼續隔離排除；本次只記錄模型輸出，不用其標籤計分。其餘 9 個不同輸入沒有本次確認可用的完整事件 GT，維持 **UNREVIEWED／未正式計分**。其中 test2 W08、test8 W06、test9 W03 另作助理視覺診斷，不新增正式標籤。

### 八個評估面向

1. **目標辨識：** 大量輸出只關注顯眼籃球；手機僅在 test2 W01 的 parsed observations 出現。test2 W08 影像可見手中手機，模型寫成 brush。沒有任何輸出獲得 phone_01 身分授權。
2. **前後物理狀態：** test2 W01 的桌面描述有影像支持；兩個 known PICKUP 的手機桌面→手持觀察未被保留。沒有完整的全資料集逐物件 state GT，不能報整體狀態正確率。
3. **事件偵測：** 沒有可接受的 PICKUP/PLACEMENT 候選。兩個已知 PICKUP 沒有可用假說，但 invalid 不進 authoritative matching，也不當有效負預測。
4. **錯目標事件歸因：** 本次沒有有效事件候選，所以沒有可驗證的錯目標「事件」數；觀察偏向 distractor、漏手機與 brush 誤分類則明確存在。不能把此情況宣稱為錯目標問題已解決。
5. **缺乏支持的 state：** 多處同格同物件同列 ON_SURFACE 與 OTHER，卻沒有說明 OTHER 代表什麼；test2 W08 對後段遮擋／不可辨識物件仍整段寫 HELD。這些不能當確定物理證據。test9 的 hand 被寫 HELD 且結構 invalid，沒有擷取成正式狀態。
6. **引用品質：** 未供 aliases、截斷的連續編號、空引用均有保存。正確 alias 只驗證參照存在，不驗證 object/state 實際可見。
7. **不確定性：** 沒有 parsed UNCERTAIN status；test8 W07 的空 NO_CONFIRMED_EVENT 沒有說明不可觀察的目標。缺 uncertainty 的輸出不代填，不把遮擋後不可見推成不存在。
8. **結構合約：** strict 2／16 與物理能力分開報告。兩份 valid 都沒有事件，其中一份沒有任何 observation；不能用 schema validity 代替物理正確性。

沒有完整正例、沒有已驗證 PLACEMENT positive、非完整正例的額外預測應是 UNEVALUATED。沒有計算 accuracy、precision、recall、F1 或 hallucination rate。

## 6. Qwen A/B/C 比較

已實際核對歷史 A/B/C 在 test5 W05、test7 W05 的 6 份輸入 receipts：**各自與 VideoLLaMA 的 8 張 PNG hashes、source indices、native PTS、aliases、順序完全相同**。沒有重跑 Qwen。

| 配置 | test5 W05 | test7 W05 | 原文 strict／兩窗 |
|---|---|---|---:|
| Qwen A（歷史、不同 task/schema） | 手機 PICKUP 文字 hypothesis | 未提出手機 pickup | 0／2 |
| Qwen B（歷史、提高細節、不同 task/schema） | 仍有手機 PICKUP 文字 | 仍漏手機 pickup | 0／2 |
| Qwen C（同一 task/schema） | 有手機 ON_SURFACE→HELD 描述，但回 NO_CONFIRMED_EVENT | 有手機桌面→手持描述，但仍無 PICKUP | 0／2 |
| VideoLLaMA（本次） | alias 列舉至截斷，沒有可用手機描述 | 只寫 basketball | 0／2 |

相同 fence 政策下，Qwen C 的兩份內文可以通過 body contract；A/B 仍缺欄位。本次 matched VideoLLaMA 兩份皆無可用 body contract。提取結果全是 descriptive，不回寫歷史 parser，也不提升 strict-valid。

**真正共享 task/schema 的對照僅限 Qwen C 的兩窗。** 但模型 template、影格標籤包裝、視覺編碼器與 preprocessing 不同：Qwen C 是每張 588×336／合計 2016 visual tokens，VideoLLaMA 是 420×224／合計 3840 tokens。因此是相同來源與任務的配置對照，不是完全匹配輸入 tensor 的純模型能力消融；A/B 只提供歷史背景。不能把兩窗 Qwen 結果外推為九支影片 benchmark。

Qwen C 也有錯誤：test5 F0047 尚未清楚離開桌面，較穩定的手持證據在 F0062/F0077；後續遮擋格不應繼續寫成確定 HELD。test7 F0062 後也缺直接手機可見支持。以上為本次助理對同一組影像的分析，不改舊輸出或 GT。

**配置層面的選擇：保留 Qwen C 為後續研究基線；VideoLLaMA 本配置不升主流程，暫不採 hybrid。** 目前多模型只會增加沒有可靠 target/state grounding 的輸出，沒有實證顯示可改善 Graph 更新。

## 7. 保存檢查、程式與證據入口

- 新增下載 helper、VideoLLaMA adapter、順序執行器，以及純 CPU 結果／比較分析與獨立證據註記腳本；未修改 Qwen implementation、ObservationAdapter 契約、GT 或 Graph。
- 8,394 個本次保護檔案未變；另核對前次 563 檔保存基線，全部未變。兩組有重疊，不相加為獨立總數。
- prompt/schema、固定輸入與程式 components、下載的模型檔案 hashes 全部核對通過。16 份非空 raw、17 條目 terminal、duplicate receipt、6 組比較來源一致性皆已確認。
- 未建立新 Stage 0、人工批准流程或 CV 子系統；沒有額外 warmup／smoke 生成，沒有 Graph 寫入、commit 或 push。

| 開啟內容 | 入口 |
|---|---|
| 原始模型結果與執行回條 | [calls/](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/calls) |
| 每窗實際影格總覽（來源 pixels＋alias） | [contact_sheets/](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/contact_sheets) |
| 全部條目及 52 個未執行原因 | [dataset_inventory.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/dataset_inventory.json) |
| 逐窗 JSON 與每支影片統計 | [results_summary.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/results_summary.json) |
| Qwen 同政策解析與來源證明 | [qwen_comparison.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/qwen_comparison.json)、[comparison_verification.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/comparison_verification.json) |
| 保存／component 檢查 | [verification.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/verification.json)、[input_freeze.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/videollama3_full_v1/input_freeze.json) |
| 新模型 adapter | [videollama3_adapter.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/experiments/videollama3_adapter.py) |
| 資料準備與可續跑執行 | [run_videollama3_dataset.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/scripts/run_videollama3_dataset.py) |

固定 prompt SHA：`ef69002cd66cf61f1448fa741cbf52f4f712d5d7b5ac09fcea0c1d1f1061da1b`。

固定 schema SHA：`6c929159a5259a82ee9312fe839d3d1cd12fc7bd1cbe8929f730495270599730`。

輸入快照 SHA：`1a39f0251f96845b7318e96f95f096680ccc6ca59169702de83bc21afeec6355`。這是實驗重現用快照，沒有新增 protocol approval checkpoint。

## 8. 剩餘限制與單一步驟建議

沒有執行端相容性 blocker：官方模型已在本機實際完成推論。剩下的是**狀態／目標觀察不足、結構合約不足、引用失真，以及 GT 覆蓋不足**；52 個空配置視窗的擴充需要另行定義資料採樣，不能假裝這次已測。

**下一步只建議：對 test5/test7 同一組固定影格，人工盲評 Qwen C 與 VideoLLaMA 的逐物件 state／alias 支持程度。** 將可見桌面、可見手持、遮擋未知逐格區分，再決定 observation contract 的後續修正；本次不自行啟動新推論或改 prompt。

VLM 仍只提供 physical-event hypotheses；目前沒有任何結果能直接作為身分授權、確定物理事件或 Memory Graph 更新。
