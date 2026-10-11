# FindMind 標註工具 — uv 快速啟動（Windows）

**推薦使用此方式**：只需要安裝 [uv](https://docs.astral.sh/uv/getting-started/installation/)，不需先安裝 Python，也不需要手動執行 `py -3.12`。

## 第一次使用

1. 確保 GitHub 的 `annotation_handoff/pass_t_phase2a_v2` 資料夾及影像已完整下載。此目錄的資料與 `release_receipt.json` 必須保留原樣。
2. 開啟 PowerShell，一次性安裝 uv：

   ```powershell
   winget install --id astral-sh.uv -e
   ```

   安裝後重新開啟 PowerShell 或檔案總管。

3. 在交接資料夾**雙擊 `Start_Annotation_UV.cmd`**。腳本會自動：
   - 使用 uv 建立 `.venv`（缺少相容 Python 時由 uv 自行下載 Python 3.13）
   - 安裝 `requirements.txt` 中指定的套件版本
   - 檢查 Tkinter 能否真的建立視窗
   - 呼叫 `review.py check` 驗證原始交接包
   - 啟動繁體中文事件標註 GUI

4. 用同一個 reviewer ID 完成七段影片；遵守原本 README 和凍結 V2 政策。
5. 完成後雙擊**原本的 `Return_Annotations.cmd`**，把建立的 ZIP 和 SHA256 傳給負責人。此回傳工具沿用 uv 建立的 `.venv`，不需另外安裝 pip 或 Python。

## 常見問題

**找不到 uv**：重新開啟 PowerShell，執行 `uv --version`。若尚未安裝，執行上方 winget 安裝指令。啟動器也會檢查 `%USERPROFILE%\.local\bin\uv.exe`。

**`.venv` 已存在但損壞／版本不相容**：先備份重要回覆，再將**僅** `.venv` 資料夾重新命名（例如 `.venv_old`），重新雙擊 uv 啟動器。絕對不要刪除 `responses/`、`validated/`、`returns/` 或交接素材。

**Tkinter/Tcl 測試失敗**：代表該環境尚不能啟動桌面 GUI；不會自動改寫任何人類標註。請將完整錯誤訊息傳給負責人。

**HANDOFF_FILE_CHANGED_OR_MISSING**：表示原本校驗檔案或影像缺漏／內容不同。新啟動器不會繞過 hash 檢查，不要編輯凍結 policy/schema、manifest、影格或 receipt。

## 為什麼新增啟動器，不直接覆寫舊版？

原本 `Start_Annotation.cmd` 和 `README.md` 的 SHA256 已被 `release_receipt.json` 保護。修改會破壞交接包的完整性檢查。因此新增 **`Start_Annotation_UV.cmd`** 與本說明；沒有修改原始 policy、schema、來源影格、事件標註資料與回傳規格。

### 相容性說明

- uv 管理 Python；這份腳本要求 3.13 建立新環境，避免直接依賴系統的 Python 3.12／3.14。
- `uv pip install -r requirements.txt` 安裝既有精確指定的直接依賴與其相依套件；不會變更 requirements 檔案。
- 程式碼與 GitHub 上的檔案已更新，但尚未在標註者的 Windows 裝置執行實機端對端測試。應先以 `HANDOFF_INTEGRITY_OK` 和 Tk GUI 實際開啟確認。
