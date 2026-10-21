# Phase 9.1 — 使用與發佈說明

[專案 README](../../README.md) · [最新報告](../../WORKSPACE/VLMtest/LATEST_REPORT.md) · [驗收完成時的正式報告](PHASE9_1_REPORT.md)

## 使用

在已配置本機環境的專案根目錄執行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_findmind_demo.ps1
```

開啟 http://127.0.0.1:8514/，選取已有記憶，再選 **Memory Graph / 記憶圖譜**。找物結果可直接帶入對應原始紀錄；點節點／關係看同格影像，拖曳平移、滾輪縮放，或用類別／時間／狀態篩選。這是唯讀候選記憶，沒有新增已驗證位置。

本機 SVG 元件包含在程式裡，不需要外部 CDN、圖譜資料庫或新的前端服務。完整 session 與執行環境仍需另外提供；clone 不附影片、模型、Graph 或個人清單。

## 已量測與驗證

- 32 項新 focused tests、46 項 Demo／出門流程／既有工具回歸、71 項 Phase 4–7 測試，共 **149 passed**。
- [完整 SHA 驗證](verification_full.json)：63.723 s；[metadata cache](verification_cached.json)：0.324 s。兩者只比較資產驗證，不能當成 GPU／整支影片加速。
- [Graph CPU 解析量測](GRAPH_CPU_MEASUREMENT.json)、[程式前後 SHA](SOURCE_CHANGE_MANIFEST.json)、[發佈保存驗證摘要](RELEASE_VERIFICATION_SUMMARY.json)。
- 原始測試紀錄：[新測試](focused_tests_final.log)、[Demo 回歸](demo_regression_final.log)、[Phase 4–7](phase4_7_regression.log)。[第一次回歸失敗紀錄](demo_regression.log)保留供追溯，原因與測試 fixture 修正見正式報告。
- 實際截圖：[圖譜](MEMORY_GRAPH.png)、[來源影格與 PTS](GRAPH_EVIDENCE.png)。

## 保存範圍

這次發佈程式、測試、必要量測 JSON、報告與小型截圖。原始模型／session／工作／個人狀態不發佈。`PRESERVATION_CHECK.json` 含完整展示清單，僅在原本機保留；其必要歷史檔案 hash 驗證改以 `RELEASE_VERIFICATION_SUMMARY.json` 發佈。正式報告中該原始連結因此僅能在本機開啟。

正式報告與 source manifest 的「未 commit／push」是原驗收時點紀錄，保留原文。後續版本控制狀態見 [Version Status](../../WORKSPACE/VLMtest/VERSION_STATUS.md)。
