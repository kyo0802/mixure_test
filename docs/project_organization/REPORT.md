# FindMind 專案整理報告

日期：2026-10-14（Asia/Taipei）。範圍：mixure_test_SAM。

## 現在從哪裡開始

開啟 [START_HERE.md](../../START_HERE.md)，或用檔案總管開啟 [WORKSPACE](../../WORKSPACE/)。目前工作階段是 **Pass I/T 平行標註＋實作**。

Freeze → 模型篩選 → Stage 0 Smoke → **Pass I/T 平行標註＋實作** → Qwen baseline 對照實驗 → Shadow mode → End-to-end → Memory Graph

Pass I 本輪已結案（資料取得／身分資訊受限）。Pass T Phase 2a 有限用途 DEV 事件標註與複核完成；Phase 2b Qwen NF4 合成容量與介面測試完成，協定決策尚待確認。沒有因為本次整理而提前批准 freeze 或推進到正式模型比較。

## 新的日常結構

```text
mixure_test_SAM/
├─ START_HERE.md                 ← 現況、流程與總入口
├─ WORKSPACE/
│  ├─ README.md
│  ├─ Pass_I/                    ← 結案、QC、Pilot 1、六案複核、工具
│  ├─ Pass_T/                    ← 事件政策、目前結論、Qwen 測試、待決策
│  └─ Data/                      ← 影片、標註包、回傳、基線資料入口
├─ src/                         ← 實作（原路徑）
├─ scripts/                     ← 執行工具（原路徑）
├─ configs/                     ← 設定（原路徑）
├─ tests/                       ← 測試（原路徑）
├─ evaluation/                  ← 既有評估資源
├─ tools/                       ← 既有外部工具；不擅自改第三方專案
├─ docs/
│  └─ project_organization/     ← 本次搬移與驗證紀錄
└─ archive/
   ├─ README.md                 ← 舊名稱到新位置的對照
   ├─ experiments/              ← 15 組歷史實驗，改用用途名稱
   └─ test_runs/                ← 10 組舊測試暫存
```

這張圖是日常入口，不是假稱底層已刪光。另有 7 個權限受限目錄仍會在根目錄顯示，詳見下方例外。根目錄的 Python/Git 設定檔也保留。

## 實際整理了什麼

- 實體集中 **25 個目錄、21,316 個檔案、2.17 GiB**，移動而非複製；沒有宣稱回收磁碟空間。
- 15 個舊輸出從散落根目錄改存 `archive/experiments/`，使用 `entity_fusion`、`canonical_pipeline_sources` 等用途名稱。完整映射在 [archive/README.md](../../archive/README.md)。
- 10 組可讀取的舊測試暫存集中到 `archive/test_runs/`。
- 建立 **32 個中文命名捷徑**及對應 Markdown 索引，指向唯一原檔，避免報告／人工標註複製後分叉。
- **55 個根目錄入口設為 Windows Hidden**：舊相容路徑、底層 artifacts/outputs、執行環境、模型、原影片與歷史說明。顯示隱藏項目仍可看到；位置與內容沒有因隱藏而失去。
- `artifacts/pass_i/`、`artifacts/pass_t/` 的版本與 SHA 路徑仍是追溯用的權威儲存。現在透過 WORKSPACE 的用途名稱進入，不需自行猜哪個版本最新。
- 保留歷史 README.md、CURRENT_PIPELINE.md 的原始內容與雜湊；這些描述的是過去狀態。今日入口為 START_HERE.md。

## 為什麼保留底層相容路徑

Pass T 直接讀取 `outputs_v292`，其他歷史輸出也是基線、測試與證據鏈的一部分。這次將實體放到 archive，原位置建立 Windows directory junction，兩邊指向同一份檔案；不是雙份資料。

凍結資料、source metadata、人工答案、prompt 與既有 receipt 沒有為了好看而改名或重新產生。版本／SHA 不再作為人的日常入口，但仍保留供驗證。程式、腳本和既有測試未因整理改寫。

## 驗證

- 搬移檔案與現行程式／設定／測試、歷史根目錄文件、Pass I 報告、Pass T 報告和 Phase 2a 契約，共 **21,828 檔案**逐檔 SHA-256 核對；最終結果見 [verification.json](verification.json)。這是列明範圍的核對，不是整顆硬碟的掃描。
- 25 組相容目錄驗證為同一實體；所有舊路徑仍能讀取。
- 32 個捷徑目標皆存在且與規格一致；Markdown 索引引用同一批目標。
- 4 個現行 CLI 的 `--help` 均可正常載入：Pass I Pilot 1、Pass T Phase 2a、Phase 2b、Qwen NF4。
- Phase 2a frozen policy/approval gate 通過；Phase 1c 的 AllowedReader 可透過舊路徑讀取 test1 target binding。
- Git 既有 tracked 狀態與搬移前一致。原根目錄 `.gitignore` 保留原始 bytes；忽略重複 archive/捷徑的規則位於新資料夾自己的 `.gitignore`。
- 沒有模型推論、人工標註變更、資料集重建、Frozen 影像操作、V297 改動、Memory Graph 寫入、commit 或 push。

CLI／路徑檢查不是完整端到端模型測試；本次未重新執行研究實驗。

## 保留例外與限制

7 個舊暫存目錄的內容無法完整讀取，未更改 ACL、未強制刪除。它們沒有納入已搬移計數：

- `.identity_focused_tmp`
- `.identity_test_tmp_baseline`
- `.identity_test_tmp_final`
- `.identity_test_tmp_full`
- `.identity_test_tmp_release`
- `.identity_unit_tmp`
- `.identity_unit_tmp_v2`

其中可改顯示屬性的目錄已隱藏，其餘仍顯示。另 `.pytest_cache` 的隱藏屬性也因存取被拒而未更改。完整結果見 [visibility_changes.json](visibility_changes.json)。

Windows junction 與 `.lnk` 是這台電腦的整理方式，不是可攜帶的 Git 資料格式。Git 仍沿原路徑追蹤同一批原檔；archive 實體副本路徑及捷徑均排除重複提交。其他機器 clone 不會自動具有此本機佈局；Markdown 導覽仍指向原 canonical 路徑，可讀且不依賴捷徑。此工作沒有 push 大型資料。

Pass T 的「DEV 事件資料原始匯出」必須與「複核補充」一起讀取；未生成另一份冒充最新 GT 的副本。A/B 非完整事件清單、隔離案例、formal eligibility 限制仍保留。

## 後續放檔規則

1. 人工找資料只從 WORKSPACE 進入；進度更新直接維護 START_HERE.md 與各 README。
2. 程式繼續放 src/scripts/configs/tests，避免在實驗結果資料夾另開正式實作。
3. 現行 Pass I/T 的原始輸出留 artifacts/pass_i 或 artifacts/pass_t；不可覆寫證據才新增 run。同步更新工作區索引，讓人不需要猜 run 名。
4. 不再在根目錄開新的 outputs_vXXX。歷史成果集中 archive；archive 內仍可能有當前依賴，不當作可任意刪除的垃圾桶。
5. 執行環境和權重不進 WORKSPACE，不複製到每個實驗資料夾。

## 追溯／復原資料

[move_journal.json](move_journal.json) 記錄每一組舊位置、新位置與數量；[visibility_changes.json](visibility_changes.json) 記錄原顯示屬性；本機 before.json 保存逐檔核對值。這些是整理用紀錄，不是新的模型 protocol freeze receipt。

需還原時應先確認 junction 仍指向記錄的 archive 目標，再非遞迴移除連結並把同一目錄搬回，最後還原可修改的顯示屬性。勿遞迴刪除 junction。organize.ps1 是本次一次性搬移程序，不應對已整理完成的目錄再次執行。
