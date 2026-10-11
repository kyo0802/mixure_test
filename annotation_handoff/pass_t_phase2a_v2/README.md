# FindMind — Pass T Phase 2a V2 人工事件標註交接

這是可獨立啟動的 **Windows 桌面標註工具**。目前任務：完成 **7 個 DEV 事件視窗**的第一輪人工審閱。採用已凍結、已核准的 V2 政策；工具不會執行模型。介面主要為繁體中文，資料 enum 保留英文。

**不用 GPU、模型、原始整支影片或原專案環境。這不是 Streamlit 網站，請直接開桌面視窗，不要連到 `127.0.0.1:8511`。**

## 1. 取得工具

在 PowerShell 執行以下命令，可只下載這個資料夾及必要影像，避免下載舊實驗與完整 Git 歷史的素材：

```powershell
git clone --filter=blob:none --sparse --single-branch --branch codex/pass-i-current https://github.com/kyo0802/mixure_test.git FindMind-annotation
Set-Location FindMind-annotation
git sparse-checkout set annotation_handoff/pass_t_phase2a_v2
Set-Location annotation_handoff/pass_t_phase2a_v2
```

也可以請專案負責人直接提供整個 `pass_t_phase2a_v2` 資料夾；子資料夾必須完整。素材約 447 MB，首次下載需要一些時間。

## 2. 第一次啟動

安裝 **Python 3.12（含 Tcl/Tk）**。Windows 官方 Python 安裝程式的預設安裝通常包含 Tk；請勿使用只有命令列且缺少 Tk 的精簡 Python。

在工具資料夾雙擊 **`Start_Annotation.cmd`**。第一次會建立本機 `.venv`，只安裝 Pillow、jsonschema 與其小型相依套件，核對素材後開啟桌面工具。之後仍雙擊同一個檔案即可。

若要手動啟動，在這個資料夾的 PowerShell 執行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B review.py check
.\.venv\Scripts\python.exe -B review.py gui
```

`check` 應顯示 `HANDOFF_INTEGRITY_OK`、`eligible_windows: 7`。第一次 `valid_round1: 0` 是正常的。若缺少影像或出現 hash 錯誤，請重新取得完整工具，勿修改 JSON 或影像來繞過檢查。

## 3. 標註範圍與政策

先閱讀 [凍結 V2 政策](artifacts/pass_t/phase2a/v2/contracts/EVENT_GT_ANNOTATION_POLICY_V2.md)。本文件是操作說明；判定依據以凍結政策及 semantic validator 為準。

| 原視窗 | 當窗 local target ID | 授權影格 | 張數 |
|---|---:|---|---:|
| test1 W03/W05（同一窗） | 17 | S000157–S000263 | 107 |
| test2 W01 | 43 | S000180–S000287 | 108 |
| test3 W07 | 54 | S000402–S000509 | 108 |
| test5 W01 | 31 | S000162–S000233 | 72 |
| test5 W05 | 44 | S000342–S000449 | 108 |
| test7 W05 | 32 | S000373–S000479 | 107 |
| test8 W07 | 74 | S000936–S001053 | 118 |

總計 7 視窗、7 不重疊證據群、6 支來源影片、728 張 full-rate 影格、16 張參考圖。test8 W06 被排除，沒有交付素材；Frozen 不在任務內。Local ID 僅定位當窗目標，不代表全域 `phone_01` 身分。

## 4. 每個視窗怎麼做

1. **審閱者 ID**：填你自己的固定代號，例如 `annotator_alex`，7 窗都使用同一代號。不要冒用先前審閱者的 `reviewer_01`。表單不會自動帶入答案。
2. **先看完整授權窗**：左側播放、逐格前後切換或使用滑桿；右侧可捲動。預設只顯示指定 candidate 的框；框可以關閉。看不清楚時用原解析度檢視。目前視窗以外的影格不能補看。窗前參考圖可以輔助辨識，但不能當事件時間／狀態引用。
3. **建立引用**：在直接支持判斷的影格填入可見內容、目標關聯與引用種類，再加入 BEFORE、TRANSITION、AFTER、STATE 或 COVERAGE 引用庫。引用使用精確 frame ID/native timestamp。單純看到偵測框不等於你已確認目標關聯。
4. **整窗判定**：選擇 `CONFIRMED_EVENTS`、`NO_CONFIRMED_EVENT`、`INSUFFICIENT_EVIDENCE` 或 `TARGET_NOT_OBSERVABLE`。只允許 `PICKUP`（拿起）與 `PLACEMENT`（放下）事件；其他動作另記觀察。每個事件需要 BEFORE/AFTER 等直接證據，以及精確轉換影格或保守時間區間。事件消失不等於拿起或放下。
5. **狀態、位置、能見度分開填**：最後確認的物理狀態與窗末能見度是不同欄位。只能引用窗內直接可見資訊；不知道就記 UNKNOWN／uncertainty。若要標位置，用左側 POINT 點擊或 BBOX 拖曳，工具不會複製 tracker 框。
6. **完整性聲明**：`CONFIRMED_EVENTS` 的完整性有 `EXHAUSTIVE_ATTESTED / NOT_ATTESTED / UNKNOWN`。只有看完整窗、標完所有可確認拿起／放下、且無可能藏事件的能見度／目標關聯／時間缺口時，才能逐項勾選 exhaustive 聲明；起／中／末引用本身不能證明連續可判定。`NO_CONFIRMED_EVENT` 也需要全窗可判定與明確負事件聲明。有缺口就記非完整或未知，不要因為表單要求而猜答案。
7. **檢查再提交**：填人工理由、uncertainty、觀察依賴性、實際 exposure 聲明等欄位；按「合約檢查」查看缺漏。通過後才能「永久提交」，並確認是親自審閱的答案。**提交後不能覆寫；未提交草稿在切窗或關閉時不會自動保存。** 若已提交但发现錯誤，保留原檔並告知專案負責人，不要手動修改。

已提交的視窗不會顯示舊答案，保存按鈕會停用。完成一窗後切到下一窗，直到 7/7。

不要查看舊人類答案、模型預測、GT、未授權的整支影片、其他未交付材料來輔助判斷。若實際已看過任何受限材料，必須如實聲明；檢查器通過只表示符合合約，不證明視覺判斷正確。

## 5. 確認進度並回傳

```powershell
.\.venv\Scripts\python.exe -B review.py progress
```

完成時應為 `valid_round1: 7`、`invalid_records: 0`。雙擊 **`Return_Annotations.cmd`**，或執行：

```powershell
.\.venv\Scripts\python.exe -B review.py return
```

工具會建立 `returns/pass_t_annotations_<UUID>.zip`，並顯示檔案位置與 SHA256。**把該 ZIP 和 SHA256 回傳給專案負責人**；不需要 push、不用傳 `.venv`、也不用重新傳影像。ZIP 包含人工提交、各提交 hash receipt、進度與來源 manifest/policy hash，未包含圖像或模型。

若負責人要求提前回傳部分工作，可使用 `review.py return --partial`；ZIP 明確標示未完成。每次回傳都建立新檔，不覆寫任何提交。不要讓多人共用同一組 `responses` 資料夾；每個審閱者保有自己的副本並分别回傳，以免同窗同輪衝突。

人工提交保存於 `artifacts/pass_t/phase2a/v2/responses/`，對應驗證收據在 `validated/`。它們與 `returns/` 已設為 Git ignore。備份／移動工具時請保留這些資料夾。若工具說重複或無效紀錄，請交由負責人處理，不要刪檔重填。

## 6. 重複審閱與限制

這次先完成 7 窗第一輪。凍結 repeat subset 為 test1 W03/W05 與 test5 W05，建議至少隔 7 天、同一位審閱者、不看舊答案，再由負責人安排第二輪（`review.py gui --round 2`）。不要現在自行補第二輪。

程式、政策、schema、原 manifest/item/backend 和素材都是原 Stage B 的 byte-identical snapshot。新 `release_receipt.json` 核對交接檔案；套件內 `stage_b/protected_before.json` 只保護這個獨立交接資料夾，**不是原專案的完整 preservation baseline**，原專案 baseline 未修改。凍結文件內不准 commit/push 的文字是當時 scope；此次交接由負責人後續的明確 GitHub 分享要求授權，未改動凍結文件。

此 DEV 標註不會寫 Memory Graph，不會授權全域 identity merge，也不會自動匯入或升格 GT。所有窗的 binding causality 仍 `CAUSALITY_UNVERIFIED`，formal eligibility 仍 0。7 窗不是 7 個已證明獨立的拍攝 session；事件預期選樣與缺少 negative controls 的限制仍保留。
