# Phase 2b — Real DEV Qwen NF4 V1D Exploratory Pilot

更新：2026-10-15T08:11:36.370538+00:00。權威來源：`artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/report_v1_20261015`。

## 執行結論

**PASS_T_PHASE2B_V1D_REAL_DEV_PILOT_COMPLETED**。保存完整 call 回條 18/18；full strict 通過 10/18。
Supervisor stop reason：`None`；worker exit code：`0`。
未完成 call IDs：`[]`；generation retries：0。各筆狀態以下表及原始 supervisor receipt 為準。
Strict-invalid 不是 NO_EVENT，未納入 authoritative structured matching；模型推論完成也不代表事件正確。

## 授權、設定與完整性

### 關鍵數字

- 完成 18/18；執行失敗 0；NOT_EXECUTED 0；所有 runtime receipt error 為 null，worker exit 0，無 guard stop。
- JSON syntax 18/18 通過；full strict 10/18（55.6%）；strict-invalid 8/18（44.4%）。通過者全部是 NO_CONFIRMED_EVENT；沒有 strict-valid event-bearing prediction。
- 5 筆 PICKUP 假說（calls 1、3、4、8、10）全部 strict-invalid，不能作正式事件匹配。不是模型完全沒提出事件，也不是已證明事件正確。
- Known-PICKUP 的 6 次表示測試中，只有 call 2 strict-valid，其輸出 NO_CONFIRMED_EVENT，於 0、0.2、0.5 秒都沒有匹配 EVT001；其餘 5 次 invalid，匹配 unavailable，不能當成五個有效漏檢結果。
- 3 個 strict-negative × 3 種表示共 9 calls：8 次 strict-valid，case alerts 均 false；test1 Multi-image（call 12）invalid，警示狀態 unavailable，不能稱 9/9 沒有誤報。
- test8 uncertain：Storyboard（call 14）為 strict-valid NO_CONFIRMED_EVENT；Native（call 6）與 Multi-image（call 11）因空 window citations invalid。三者都不支持完整負例結論。
- 全程 supervisor 取樣約 485.10 秒（8 分 5 秒）；global GPU used 取樣峰值 8.85 GiB；per-call inference allocated 峰值 6.32 GiB；owned RSS 峰值 4.69 GiB，available RAM 最低 14.11 GiB。

因此 execution reliability 已在本次 18 calls 示範可完成；event-bearing structured-output contract 仍是實際限制，physical-event correctness 尚未人工審定。這份小型 DEV 結果不足以對模型能力或泛化作正式結論。

- Protocol canonical SHA-256：`b7929b0e6ecaa651d7a316e838efe0b4c6437920a93b5b33bf41b6ce34740c9d`。
- Authorization canonical SHA-256：`eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f`；reviewer：`reviewer_0`。
- 既有 local Qwen2.5-VL-7B-Instruct NF4；immutable V1D/V2；Uniform8、Reference NONE、C3；greedy、seed 42、max_new_tokens 1024。
- Multi-image8 / Storyboard8 / Native Video Array8；Native 為 FRAME_MATCHED_ONLY，8 source frames 對應 4 temporal units，不代表八個獨立 temporal positions。
- 固定 source PTS 為 authoritative；每筆 provenance、alias mapping、rendered text、processor/tensor records 保留於 call/runtime receipts。
- 凍結元件在分析前後通過原有 verify_frozen；private GT/eligibility 的分析前後 hash 一致。未修改 prompt、GT、validator、runtime 或 Memory Graph。
- 媒體完整性只對實際成功 load_envelope 的 call 適用；未執行者不得稱已驗證。runtime_receipt_error 另列於 CALL_ANALYSIS.json。

## 固定 cohort

| 視窗 | item_id | 允許用途 |
|---|---|---|
| test1 W03/W05 (dedup) | PT2A_9d15d2a6b56b56d0 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS |
| test2 W01 | PT2A_b35d807b28b92101 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS |
| test5 W01 | PT2A_fe0910d66f4c5614 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS |
| test5 W05 | PT2A_eb60192e6986cb4f | KNOWN_EVENT_MATCHING_ONLY |
| test7 W05 | PT2A_c58b4df88a2f6801 | KNOWN_EVENT_MATCHING_ONLY |
| test8 W07 | PT2A_5dbb180e8ff88762 | DESCRIPTIVE_UNCERTAINTY_ONLY |

test3 W07 排除；test1 W03/W05 為一個去重單位。兩個 known-PICKUP 視窗非 exhaustive；test8 為 uncertain；無 validated PLACEMENT positive。

## 18-call 結果

| call | 視窗 | representation | 執行狀態 | 分類 | 模型 outcome | generation 秒 |
|---|---|---|---|---|---|---|
| 1 | test5 W05 | NATIVE_VIDEO_ARRAY | STRICT_INVALID | STRICT_INVALID | CONFIRMED_EVENTS | 112.39 |
| 2 | test7 W05 | MULTI_IMAGE | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 70.01 |
| 3 | test5 W05 | STORYBOARD | STRICT_INVALID | STRICT_INVALID | CONFIRMED_EVENTS | 105.4 |
| 4 | test7 W05 | STORYBOARD | STRICT_INVALID | STRICT_INVALID | CONFIRMED_EVENTS | 12.3 |
| 5 | test1 W03/W05 (dedup) | STORYBOARD | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.77 |
| 6 | test8 W07 | NATIVE_VIDEO_ARRAY | STRICT_INVALID | STRICT_INVALID | NO_CONFIRMED_EVENT | 4.61 |
| 7 | test2 W01 | NATIVE_VIDEO_ARRAY | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.84 |
| 8 | test7 W05 | NATIVE_VIDEO_ARRAY | STRICT_INVALID | STRICT_INVALID | CONFIRMED_EVENTS | 8.74 |
| 9 | test5 W01 | NATIVE_VIDEO_ARRAY | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.93 |
| 10 | test5 W05 | MULTI_IMAGE | STRICT_INVALID | STRICT_INVALID | CONFIRMED_EVENTS | 37.16 |
| 11 | test8 W07 | MULTI_IMAGE | STRICT_INVALID | STRICT_INVALID | NO_CONFIRMED_EVENT | 5.02 |
| 12 | test1 W03/W05 (dedup) | MULTI_IMAGE | STRICT_INVALID | STRICT_INVALID | NO_CONFIRMED_EVENT | 6.27 |
| 13 | test2 W01 | STORYBOARD | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.77 |
| 14 | test8 W07 | STORYBOARD | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.79 |
| 15 | test2 W01 | MULTI_IMAGE | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 6.51 |
| 16 | test1 W03/W05 (dedup) | NATIVE_VIDEO_ARRAY | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.77 |
| 17 | test5 W01 | MULTI_IMAGE | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 6.43 |
| 18 | test5 W01 | STORYBOARD | VALID_NO_CONFIRMED_EVENT | VALID_NO_CONFIRMED_EVENT | NO_CONFIRMED_EVENT | 5.82 |

## 分階段 strict 驗證

| stage | status counts |
|---|---|
| JSON_SYNTAX | {'PASS': 18} |
| SCHEMA | {'FAIL': 8, 'PASS': 10} |
| SEMANTIC | {'NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE': 8, 'PASS': 10} |
| CITATION | {'NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE': 8, 'PASS': 10} |
| FULL_STRICT | {'FAIL': 8, 'PASS': 10} |

Schema 失敗時 semantic/citation 標為 NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE，不得視作通過。Raw 未修復或補欄、未發明 citation。未輸出、strict-invalid、valid NO_CONFIRMED_EVENT 分別保留。

## 模型提出的事件假說與 citation（不是人工確認）

原始 schema failures：calls 1/3/4/8/10 的 event timing_uncertainty 與 window uncertainty 為空字串；call 10 另有四位 event ID `PRED_EVT_0001`；calls 6/11 為空 window_cited_frame_aliases；call 12 為空 uncertainty。全部保持原樣，沒有補填。

事件時間 alias 對應原始 source PTS（僅做 private/report mapping，不補救 invalid prediction）：

| call | alias | source frame | native source PTS（秒） |
|---|---|---|---|
| 1 | F0001 | S000342 | 11.4 |
| 3 | F0001 | S000342 | 11.4 |
| 4 | F0001 | S000373 | 12.435 |
| 8 | F0001 | S000373 | 12.435 |
| 10 | F0077 | S000418 | 13.933333333333334 |

Calls 1 與 4 的 rationale 分別使用「card」與「ball」。這是原始輸出中的文字性 target-grounding 疑點，需日後對照影像人工複核；本次不把它自動裁定為錯誤目標或真實物理事件。

| call | type | timing | citations | 模型 rationale | 可用範圍 |
|---|---|---|---|---|---|
| 1 | PICKUP | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | ['F0001'] | The card is picked up from the table. | STRICT_INVALID_DESCRIPTIVE_ONLY |
| 3 | PICKUP | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | ['F0001'] | The phone is picked up from the surface. | STRICT_INVALID_DESCRIPTIVE_ONLY |
| 4 | PICKUP | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | ['F0001'] | The ball is picked up from the surface in frame F0001. | STRICT_INVALID_DESCRIPTIVE_ONLY |
| 8 | PICKUP | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | ['F0001'] | The object is picked up from the table. | STRICT_INVALID_DESCRIPTIVE_ONLY |
| 10 | PICKUP | {'frame_alias': 'F0077', 'status': 'EXACT_SUPPLIED_FRAME'} | ['F0077'] | The phone is lifted from the table. | STRICT_INVALID_DESCRIPTIVE_ONLY |

Physical evidence review 全部 UNREVIEWED。本報告只引用模型文字與既有 GT scope；沒有新增人工 adjudication，也沒有將 event claim 當作確證的物理轉換。

## Known-PICKUP matching：0 / 0.2 / 0.5 秒

| call | 視窗 | tolerance秒 | matches | 未匹配 known GT | 額外假說 |
|---|---|---|---|---|---|
| 2 | test7 W05 | 0 | 0 | ['EVT001'] | UNEVALUATED |
| 2 | test7 W05 | 0.2 | 0 | ['EVT001'] | UNEVALUATED |
| 2 | test7 W05 | 0.5 | 0 | ['EVT001'] | UNEVALUATED |

僅 strict-valid 且 runtime receipt 合格的輸出進入 versioned closed-interval-gap one-to-one matcher。Point-to-interval=max(a-t,0,t-b)；interval-to-interval=max(c-b,a-d,0)。未知時間、target association uncertainty 與 unsupported evidence 不補推。BEFORE/AFTER evidence brackets 不轉成推定事件持續時間。詳細匹配及 unmapped/unknown 情況保留於 CALL_ANALYSIS.json。

## Strict-negative 個案警示

| call | 視窗 | case alert | outcome |
|---|---|---|---|
| 5 | test1 W03/W05 (dedup) | False | NO_CONFIRMED_EVENT |
| 7 | test2 W01 | False | NO_CONFIRMED_EVENT |
| 9 | test5 W01 | False | NO_CONFIRMED_EVENT |
| 13 | test2 W01 | False | NO_CONFIRMED_EVENT |
| 15 | test2 W01 | False | NO_CONFIRMED_EVENT |
| 16 | test1 W03/W05 (dedup) | False | NO_CONFIRMED_EVENT |
| 17 | test5 W01 | False | NO_CONFIRMED_EVENT |
| 18 | test5 W01 | False | NO_CONFIRMED_EVENT |

只作 case-level alerts，不是 population false-positive rate。Invalid/未執行不能當作無警示。負例的額外獨立視覺品質複核有限；test1 僅局部 spot-check，test2/test5 W01 沒有新增逐格視覺複核。

## Uncertain-window 描述

| call | 視窗 | outcome | scope |
|---|---|---|---|
| 14 | test8 W07 | NO_CONFIRMED_EVENT | DESCRIPTIVE_ONLY |

test8 不當作 negative，也不作完整事件清單主張。

## Representation-specific 描述

| representation | counts |
|---|---|
| NATIVE_VIDEO_ARRAY | {'recorded': 6, 'STRICT_INVALID': 3, 'VALID_NO_CONFIRMED_EVENT': 3} |
| MULTI_IMAGE | {'recorded': 6, 'VALID_NO_CONFIRMED_EVENT': 3, 'STRICT_INVALID': 3} |
| STORYBOARD | {'recorded': 6, 'STRICT_INVALID': 2, 'VALID_NO_CONFIRMED_EVENT': 4} |

三種表示的差異僅為同一個小型 DEV cohort 的描述，不作模型排名或泛化主張。Storyboard 空間拼圖、multi-image 序列及 native 四 temporal units 的資訊表達不同。

## 資源與時間

`{'gpu_used_gib': 8.8515625, 'owned_rss_gib': 4.690132141113281, 'ram_available_gib': 14.110404968261719, 'supervised_elapsed_s': 485.10103154182434, 'sampling_note': 'Sampled values; not a guarantee that all transient peaks were captured.'}`

GPU used 含其他進程；owned RSS 含受監控 worker 子樹；runtime 的 per-call peak allocated 與 sampled global GPU usage 不同，詳見 CALL_ANALYSIS.json 與原始 runtime receipts。所有 raw outputs、失敗或未執行狀態保留，未進行 quality retry。

## 科學限制與停止邊界

本次分開報告 execution reliability、contract compliance、physical-event hypotheses 及 representation 描述。格式正確不等於視覺正確；文字中的 PICKUP 不等於已確認的物理 PICKUP。
非 exhaustive 視窗的 unmatched predictions 為 UNEVALUATED；無 validated PLACEMENT positives；small selected DEV、causality unverified、target association 與抽樣間隙均限制解讀。
不報 formal accuracy、precision、recall、F1、false-positive rate、hallucination rate 或 generalization。未新增 GT 或人工審定，未寫 Memory Graph。
依本次授權在此停止；不重跑、不修 prompt、不追加模型呼叫。

## 原始檔案

- [run_receipt.json](../run_receipt.json)：supervisor 原始結果與 resource samples。
- [CALL_ANALYSIS.json](CALL_ANALYSIS.json)：逐 call 分階段驗證、GT-scoped evaluation、hashes。
- [RESOURCE_SUMMARY.json](RESOURCE_SUMMARY.json)：資源彙整。
- [frozen_bundle.json](../frozen_bundle.json)、[authorization_use.json](../authorization_use.json)。
- 每筆 call_01…call_18（存在者）的 raw_output.txt、runtime_receipt.json、call_receipt.json 均保持原樣。
