# V2.6.1 — SAM 2.1 vs SAM 3.1 隔離對照測試報告

**狀態：依停止規則中止全量 A/B。** 七支影片與模型輸入均已凍結、驗證；官方 SAM 3.1 checkpoint 已取得並在 test8 的同一目標框上實際推論。Windows RTX 5070 Ti 上缺乏可執行的快速注意力核心，數學後端雖可運作，但 8 個取樣影格需 130–183 秒，且遮罩延續不足。因此沒有七片 SAM 3.1 完整預測、沒有後凍結實體目標複核，也沒有可宣稱的模型勝負。

## 1. Research Question

問題是 SAM 3.1 對 FindMind 的同一支手機是否提升正確目標連續性、漂移安全、YOLO 空窗恢復與實用速度。**本次不能回答完整問題**；能回答的是在目前 Windows/GPU 環境下，SAM 3.1 的官方快速推論路徑不可用，短片段 fallback 不具全量測試可行性。

## 2. V2.6 Frozen Baseline

`test3.mp4`–`test9.mp4` 的 SHA-256 全部與 `outputs_v26/baseline_manifest.json` 相符，包含目前更新後的 test5。沿用 V2.6 的 YOLO、目標綁定、候選審查、Re-ID 授權與 Identity Guard；不修改舊輸出。test7 f636 是 `PROVISIONAL_MATCH`，不得重新初始化；test8 f804 是 `CONFIRMED_MATCH`，可重新初始化。後者作為短片段探測起點。歷史 SAM 2.1 原始遮罩數不能直接當物理目標正確率。

## 3. Official SAM3.1 Technical Review

完整 28 項查證見 [SAM31_TECHNICAL_REVIEW.md](SAM31_TECHNICAL_REVIEW.md)。使用 [Meta 官方程式](https://github.com/facebookresearch/sam3) revision `2345a4ad109ac29c569da749c91d84f10dc08c40` 與 [官方 checkpoint](https://huggingface.co/facebook/sam3.1) `sam3.1_multiplex.pt`，SHA-256 `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`。官方 checkpoint 權限已驗證。官方的約 7× 敘述是單 H100、128 物件、SAM 3.1 對 2025 年 SAM 3，**不是對 SAM 2.1**。[官方 release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)。

## 4. Relevant SAM2.1 vs SAM3.1 Architectural Differences

現有 SAM 2.1 對已知 YOLO 框建立明確追蹤 ID。SAM 3.1 multiplex 影片 API 的框走視覺 grounding；點提示走明確 `obj_id` 實例路徑。SAM 3.1 加入多物件 Object Multiplex，但本實驗主要只追一支手機。兩個 SAM 內部 ID 都不能當 `phone_01` 物理身分證據。

## 5. Experimental Isolation

七支影片雜湊、目標初始化框與 V2.6 決策已寫入 [experiment_manifest.json](experiment_manifest.json)。短測 SAM 2.1 與 SAM 3.1 都取 test8 f804–f846，每 6 原影片影格取 1 張，共 8 張；輸入目標框完全相同。框提示與點提示屬**不同 SAM 3.1 探測設定**，點提示只作備選，不與主要框提示混算。未使用 GT 選點、選遮罩或修正預測。

## 6. Environment and Hardware

GPU：NVIDIA GeForce RTX 5070 Ti，16303 MiB 實體顯存，驅動 616.92。兩個環境均為 Python 3.12.8、PyTorch 2.10.0+cu128、CUDA runtime 12.8。V2.6 `.venv` 未變動；SAM 3.1 裝於 `.venv_sam31`。額外使用 Triton Windows 3.6.0.post26、FlashAttention 3 3.0.0。詳見 [environment_manifest.json](environment_manifest.json)。

## 7. Prompt Mapping

SAM 2.1：原始像素 `xyxy` 框。SAM 3.1 主要框模式：同一 `xyxy` 轉成官方 API 的歸一化 `xywh`，沒有 `smartphone` 文字提示。備選點模式：由同一凍結框中心計算一個正點，`obj_id=1`。框與點差異明列，不能歸因於模型版本本身。

## 8. SAM2.1 Baseline Implementation

沿用官方 `facebookresearch/sam2` revision `2b90b9f5ceec907a1c18123530e92e794ad901a4`、`sam2.1_hiera_small.pt` 與每 6 影格傳播設定。七片歷史輸出保持唯讀；另以同一 test8 短片段重新執行一次。短測 8/8 影格有非空遮罩，傳播 0.406 秒，PyTorch 峰值配置 0.68 GiB。非空不等於正確物件。

## 9. SAM3.1 Implementation

官方 `build_sam3_multiplex_video_predictor`、checkpoint、影片 session、`add_prompt`、`propagate_in_video`。新建的 [compat.py](../../src/memory_graph/v261/compat.py) 只修補官方 base/multiplex `offload_state_to_cpu=False` 參數不相容，並為 Windows 啟用 PyTorch MATH SDPA；Meta 原始碼未修改。官方 `flash-attn-3` 套件匯入成功，但 RTX 5070 Ti 執行時報 `no kernel image is available`。checkpoint 固定 16-slot bucket；改 `multiplex_count=1` 會權重尺寸不合。

## 10. Per-Video Results

下表是**既有 SAM 2.1 原始傳播紀錄**，不是兩模型的七片 A/B，也不是正確目標覆蓋率。

| Video | Historical SAM 2.1 nonempty / sampled | SAM 2.1 lost events | Possible drift flags | SAM 3.1 full | Paired conclusion |
|---|---:|---:|---:|---|---|
| test3 | 48/157 | 109 | 0 | N/A | NOT_MEASURABLE |
| test4 | 44/159 | 115 | 0 | N/A | NOT_MEASURABLE |
| test5 | 61/171 | 110 | 0 | N/A | NOT_MEASURABLE |
| test6 | 36/132 | 96 | 0 | N/A | NOT_MEASURABLE |
| test7 | 38/185 | 147 | 0 | N/A | NOT_MEASURABLE |
| test8 | 40/150 | 110 | 1 | N/A | NOT_MEASURABLE |
| test9 | 59/109 | 50 | 1 | N/A | NOT_MEASURABLE |

test8 另有 f804–f846 的短片段探測，見第 17 節。其餘六片沒有執行 SAM 3.1 推論，故沒有 per-video 勝負。

## 11. Correct-Target Coverage Comparison

N/A。完整七片 SAM 3.1 預測與同一複核影格的人工物理身分判定均未完成。短測僅能比較非空遮罩：SAM 2.1 8/8、SAM 3.1 框 3/8、SAM 3.1 點 1/8。這不是正確目標覆蓋率。

## 12. Drift Comparison

N/A。非空 SAM 3.1 遮罩未經實體物件複核，不能判斷是否漂到手、座機或其他物件，也不能把沒有遮罩的影格算為安全勝利。

## 13. Occlusion / Viewpoint Comparison

N/A。完整遮擋與視角事件序列未跑完。

## 14. YOLO-Gap Recovery Comparison

N/A。未對同一組可見目標與 YOLO 空窗影格做後凍結複核。

## 15. Test7 Safety Regression

凍結 V2.6 test7 f636 仍是 `PROVISIONAL_MATCH`，不授權 SAM 重新初始化；[V2.6 的 16 項安全回歸測試](../../tests/test_v26_safe_fusion.py) 已通過。本次沒有 test7 的 SAM 3.1 完整傳播，因此其全流程回歸仍待驗證。

## 16. Test8 Post-ReID Comparison

f804 的 `candidate_009` 在 V2.6 是 `CONFIRMED_MATCH`，因此雙方短測使用相同授權事件與 YOLO 框。既有 SAM 2.1 的完整 post-ReID 段落有 28/50 非空遮罩；本次 8 個影格的短測：SAM 2.1 為 f804–f846 全部；SAM 3.1 框為 f834、f840、f846；SAM 3.1 點為 f804。**這只描述遮罩存在，不描述是否追對同一支手機。**

## 17. Runtime / VRAM Comparison

同一 RTX 5070 Ti，單次執行，未做明確 warmup；表中峰值是 PyTorch 在提示與傳播期間的配置，不是實體 VRAM 精確占用。Windows `nvidia-smi` 在慢速傳播期間顯示約 15.9/16.3 GiB 已使用，PyTorch 配置可超過實體顯存。

| 同一 8 影格 test8 探測 | SAM 2.1 | SAM 3.1 框、MATH | SAM 3.1 點、MATH |
|---|---:|---:|---:|
| 非空遮罩影格 | 8/8 | 3/8 | 1/8 |
| 模型建置（秒） | 2.670 | 13.346 | 13.975 |
| session 初始化（秒） | 0.840 | 0.140 | 0.139 |
| 提示（秒） | 5.167 | 9.787 | 13.016 |
| 傳播（秒） | 0.406 | 183.327 | 130.884 |
| PyTorch 峰值配置（GiB） | 0.68 | 21.27 | 18.27 |

SAM 3.1 的 MATH fallback 速度**不能外推**為可用 FlashAttention 環境的模型速度。七片全長約 1,063 個 SAM 2.1 取樣影格，加上 test8 重新初始化 50 個；按此短測的後段延遲直接擴展將耗費數小時且可能受顯存影響，依停止規則不再做無效全跑。

## 18. Side-by-Side Visual Results

N/A。SAM 3.1 全量預測與人工複核前置條件不成立，因此沒有製作可能誤導的七片對比 timeline/contact sheet。短測 JSON 保存影格、內部 ID、遮罩面積及機器量測；沒有像素級 SAM 3.1 遮罩檔，不能做可審查的實體目標疊圖。

## 19. Optional Object Multiplex Experiment

`NOT_TESTED`。官方宣稱 Object Multiplex 對 128 物件在 H100 相對舊版 SAM 3 有約 7× 效率提升；單手機主實驗尚未完成，故不進行多物件探索，也不把官方 benchmark 當本專案測速。

## 20. Current Phone-Tracking Value

在目前 Windows RTX 5070 Ti 安裝上，SAM 3.1 官方快速注意力路徑不可用；數學 fallback 的成本與短測遮罩延續均不足以替換已工作的 SAM 2.1。這是**部署可行性判斷**，不是完整模型品質排名。

## 21. Future Spatial-Memory Value

Object Multiplex 的共享記憶體多物件追蹤設計，對未來同時追手機、球、盒、玩偶、瓶子等實體有研究價值；目前沒有本專案多物件實測，列為待驗證方向。

## 22. Limitations

僅七支設計影片、重複環境、主要單一手機類別、歷史人工複核稀疏且非逐像素 GT。SAM 3.1 只有 test8 短片段；框與點提示不是同一任務；Windows CUDA 注意力後端限制、顯存超額配置、冷啟動與未 warmup 都影響速度。沒有完整預測凍結後的人工遮罩複核，無法評估正確身分、漂移、遮擋或 YOLO-gap 恢復。不能推論通用 SAM 品質或其他 GPU 效率。V2.6.1 證據完整性與 V2.6 安全回歸合計 **31 passed、1 skipped**；跳過項目是因全量雙模型人工複核並未完成。

## 23. Final Recommendation

**`INSUFFICIENT_EVIDENCE`**。完整 V2.6.1 A/B 未完成，不能聲稱 SAM 2.1 在一般情況優於 SAM 3.1。原型目前繼續沿用凍結的 SAM 2.1；若要完成模型選擇，需在 SAM 3.1 快速注意力可執行且顯存足夠的環境中，依 [實驗計畫](../../docs/superpowers/plans/2026-09-26-v261-sam21-sam31-ablation.md) 重跑七片、先凍結預測，再用相同複核影格評估實體目標正確性。阻礙細節見 [SAM31_RUNTIME_BLOCKED.md](SAM31_RUNTIME_BLOCKED.md)。
