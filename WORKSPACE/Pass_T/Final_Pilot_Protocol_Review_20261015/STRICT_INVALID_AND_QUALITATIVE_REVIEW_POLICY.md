# Strict-invalid and Qualitative Review Policy — prospective

Review 67b59d603e36；**awaiting human approval**。不修改 parser/schema/validator/GT，不重寫既有結果。

## Non-negotiable storage and eligibility

1. 每次模型回傳raw bytes原樣保存（含invalid JSON/Markdown/缺欄），記SHA、call ID、runtime/processor receipt、耗時/錯誤；不得strip、補JSON、填空uncertainty、發明citation或重新生成。
2. 分開報 JSON_SYNTAX、SCHEMA、SEMANTIC、CITATION、FULL_STRICT。權威 validator E23 在 schema failure 會early return；因此後續stage未跑時是 NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE，不是假PASS或自動FAIL。若用既有collect-all helper，只能另列非權威diagnostic，不替換strict結果。
3. **只有FULL_STRICT=PASS且必要來源/引用mapping可驗證**的結構化結果，才能進authoritative matching。validity是格式/合約資格，不是physical truth認證。
4. 任一strict-invalid不得進authoritative matching；不得轉成NO_EVENT、模型abstention、零事件成功或自動FN。該單位matching記UNAVAILABLE_STRICT_INVALID，known GT保持未評估；保留無法產生可用結構的原因。
5. timeout/OOM/無raw/未執行，分別MISSING_TIMEOUT、MISSING_RUNTIME_FAILURE、NOT_EXECUTED_AFTER_STOP等；記已計畫18、已開始、完成、可解析、strict-valid及各層分母。不得以只剩少數valid的分母產生正式模型metrics。
6. generation-quality retry=0、automatic text repair=0、field filling=0、validator weakening=0；proposed transport retry=0，避免隱藏重複生成。strict-invalid在硬體健康時繼續固定計畫剩餘call；硬體/程序/timeout停止則保留剩餘NOT_EXECUTED。

## Authoritative structured matching — only applicable units

- 三 strict negatives：full-strict valid下報case-level event alert與人工支持審查；不是母體FP率。invalid不當negative成功。
- 兩known PICKUP：只match既有supported_positive_event_ids及同event type；target_association_uncertainty必須NONE（現有matcher條件），這個模型欄位本身不證明身分已正確；實際association仍需定性檢視。未列出的predicted events全部UNEVALUATED，不自動FP。
- test8 uncertain：不作event-list matching或negatives，只描述outcome、abstention與hypotheses。
- 禁止test3 W07進模型或matching。
- 各0/0.2/0.5秒均報；source native PTS authoritative。EXACT_FRAME是point，BOUNDED是closed evidence bracket，不推duration/midpoint；TIMING_UNKNOWN不能產生定時match。
- 提議採 `require_overlap=False`、greedy one-to-one，同type、closed-interval gap=`max(0,GT_start-PRED_end,PRED_start-GT_end)` ≤ tolerance；按(distance,GT index,pred index)排序，GT/pred各用一次，duplicate不多算。不是optimal maximum-cardinality；點在GT區間內的距離應為0，區間相交/端點相接亦為0；這只是時間相容，不證明事件或duration。
- **T04未解**：E30既有公式用strictly positive overlap length判斷相交，對GT有寬度、pred是內部point時會改用到endpoint的非零距離，與上述closed-interval規則不一致。這是靜態source可見的邊界缺口，未用真實GT或新增fixtures執行測試；本次不修matcher、不假稱新規則已實作，也不能悄悄採錯誤legacy行為。必須在freeze/scoring前另獲授權處理並重審hash。
- 無validated PLACEMENT positive；PLACEMENT假說只有個案定性價值，不生造新GT。

## Separately labeled qualitative review

對**strict-valid與strict-invalid分開**看現有raw事件假說，原raw/strict狀態永久保留。invalid中的文字可人工描述，但不能自動修成權威prediction或納入GT matching。

每一review項應記：call/representation、原raw SHA與原文引用、original validation status、可辨識的claim（無法解讀則UNINTERPRETABLE）、cited supplied aliases、可見physical transition與target association的支持/反證/缺口。結論用 SUPPORTED / NOT_SUPPORTED_BY_SUPPLIED_EVIDENCE / INDETERMINATE / UNREVIEWED；列實際reviewer及引文。沒有人工看過就維持UNREVIEWED；本任務未做real-pixel review，沒有新增任何此類標註。

定性結論是人對證據支持度的描述，不是authoritative structured prediction、不回填schema、不覆寫Phase2a GT、不自動稱hallucination/FP。不要因無相符特徵、遮擋或uncertainty字串為空就直接裁定physical event錯誤。

## Required disclosure

V1D synthetic regression **8/8 JSON、1/8 full strict；6/8 event-bearing全strict-invalid；9 timing空、6root空、1window cites空**。預期real pilot可能多數結構不可用；這不能透過repair或只報valid子集隱藏。定性假說研究仍需人工明確接受H01風險，不代表structured baseline已達標。
