# 新影片處理與查詢

[完整中文報告](PHASE7_REPORT.md) · [驗證與 hashes](VERIFICATION.md) · [日常入口](../../WORKSPACE/VLMtest/LATEST_REPORT.md)

從 repository root 使用既有 `.venv`。需要現有 YOLO11s、Qwen NF4、SAM2.1 small 與 Ubuntu WSL Nemotron NVFP4 runtime。**沒有自動下載或安裝環境。** 模型逐一載入；本次測得 36.77 秒影片約需 12 分鐘。

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/run_findmind_video.py --video "C:\Videos\new_video.mp4" --query "Where is my phone?"
```

終端會印出 `SESSION ...` 路徑。所有資料在 `artifacts/findmind_sessions/<session_id>/`，不複製原影片。

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/run_findmind_video.py --session "artifacts/findmind_sessions/<session_id>" --query "Where is my phone?"
```

第二個命令只讀已保存的 Graph／manifest，無 GPU 模型。其他類別可查既有觀察，例如 `--query "Where is my bottle?"`；keys／wallet 的實際感知尚未驗證，不能保證有結果。`--target-category bottle` 可在首次處理時要求該類別定位。若沒有可信區域證據，回 UNKNOWN 是合法結果。

搜尋回傳時間、原片影格、框／mask、表面區域、身分狀態與不確定性。它描述歷史候選位置，不保證物品仍在原處。`--entity-id` 僅能查詢既有已授權身分，不會把類別或追蹤 ID 自動註冊成使用者物品。

失敗處理：查看 `<stage>_stage.json`、`<stage>.log`；成功輸出保留，其他階段可建立部分記憶。若收到 source／Graph hash mismatch，先檢查來源完整性；不要把不同檔案換到同一 session。新 process 命令產生新 session；目前沒有中斷任務的自動續跑模式。

實跑範例：[Graph](../findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/memory_graph.json) · [搜尋](../findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/search_result.json) · [桌面手機證據](../findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/evidence/f00000414_annotated.jpg)
