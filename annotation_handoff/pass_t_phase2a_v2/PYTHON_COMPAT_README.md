# Python 相容啟動方式（Windows）

如果雙擊原本的 `Start_Annotation.cmd` 時出現 `No suitable Python runtime found`，請改用本資料夾的 **`Start_Annotation_AnyPython.cmd`**。

這是額外新增的相容啟動器，**不是**變更凍結政策、schema、影片、annotator responses 或交接包的既有 SHA-256 檢查。

## 支援版本

Python 3.10、3.11、3.12、3.13（需要有 `tkinter` / Tcl/Tk），優先使用 3.13 → 3.12 → 3.11 → 3.10。已有相容的 `.venv` 時優先沿用。

1. 安裝以上任一個版本 Python（Windows 上正常安裝含 Tcl/Tk）。
2. 在完整交接包內，雙擊 `Start_Annotation_AnyPython.cmd`。
3. 首次啟動會建立 `.venv`、安裝原本鎖定的 Pillow/jsonschema，呼叫 `review.py check` 確認原始檔與影格完整，然後開啟 GUI。
4. 標註完成後，**仍使用原本 `Return_Annotations.cmd`** 回傳 ZIP + SHA256。

## 注意

- 如果已存在不相容／損壞的 `.venv`，先備份標註資料，再只將 `.venv` 重新命名（例如 `.venv_old`），重新執行新啟動器。**不要刪除 `artifacts/pass_t/phase2a/v2/responses/`、`validated/` 或 `returns/`。**
- 這個腳本不會繞過完整性檢查；若出現 `HANDOFF_FILE_CHANGED_OR_MISSING`，請核對是否下載到完整且一致的交接包。
- 舊固定 commit `3e8a8a4c5393a208675dc458db92f3ef2cb8e023` 不含此新啟動器。請使用下方更新後的版本或取得此新檔。
