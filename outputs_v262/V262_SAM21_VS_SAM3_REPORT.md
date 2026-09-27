# V2.6.2｜SAM 2.1 與官方 SAM 3 目標延續實驗報告

**完成狀態：** Stage A 通過；test3–test9 七支影片的三路推論、預測凍結、影像核對及比較完成。  
**最終分類：`KEEP_SAM21`。** 目前 FindMind 原型維持 SAM 2.1；SAM 3 point 留作研究支線。

## 1. Research Question｜研究問題

在既有 YOLO、V2.6 身分判定及相同 Identity Guard 不變的條件下，官方 SAM 3 是否比 SAM 2.1 更能延續**同一個實體** `phone_01`，尤其在短暫遮擋、視角改變與已確認 Re-ID 後？同時核對錯物件漂移及本機運行代價。單純產生非空遮罩不算成功。

## 2. Why SAM 3 Was Tested After V2.6.1｜改測原因

V2.6.1 的 SAM 3.1 因 Windows／RTX 5070 Ti 上缺乏可用的快速注意力執行路徑而停在短測；那不是 SAM 3 的品質實驗。本次使用官方 **SAM 3** 權重和建構路徑，先做獨立可行性測試，再依停止規則決定是否跑七支影片。

## 3. Frozen V2.6 Baseline｜凍結基準

影片為 test3–test9。沿用既有 V2.6 的 YOLO 偵測、目標 `phone_01`、候選身分判定、初始化時機與 guard；七支影片 SHA-256 已與既有基準核對。`test7 f636` 的室內電話是 `PROVISIONAL_MATCH`，不得重新初始化目標；`test8 f804` 是 `CONFIRMED_MATCH`，允許兩臂以相同凍結 YOLO 框重新初始化。歷史 `outputs_v24`、`outputs_v241`、`outputs_v25_rerun`、`outputs_v26`、`outputs_v261` 僅作讀取；新成果位於 `outputs_v262`。

## 4. V2.6.1 Historical SAM3.1 Blocker｜歷史結果

先前 SAM 3.1 在 test8 f804–f846 八影格的數學注意力後備路徑約需 **183.327 秒**，峰值配置約 **21.27 GiB**，七片 A/B 因停止規則未執行，當時分類為 `INSUFFICIENT_EVIDENCE`。此數字只作歷史背景，**不與本次 SAM 3 品質或時間作同條件三方排名**。

## 5. Official SAM 3 Technical Review｜官方技術核對

程式固定於官方 [facebookresearch/sam3](https://github.com/facebookresearch/sam3) revision `2345a4ad109ac29c569da749c91d84f10dc08c40`；權重取自受存取控制的 [facebook/sam3](https://huggingface.co/facebook/sam3)，模型 revision `3c879f39826c281e95690f02c7821c4de09afae7`、`sam3.pt` SHA-256 `9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e`。程式明確呼叫 `build_sam3_predictor(version="sam3")` 並排除 Multiplex 型別及 SAM 3.1 權重。

官方影片介面支援 box 與 point 提示。此處 box 是視覺示例，初始幀可能產生多個 SAM 局部 ID；SAM 局部 ID 不等同 FindMind 永久身分。完整研究記錄見 [SAM3_TECHNICAL_REVIEW.md](SAM3_TECHNICAL_REVIEW.md)，對應官方 [模型程式](https://github.com/facebookresearch/sam3/blob/main/sam3/model_builder.py)及[影片推論程式](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_video_inference.py)。

## 6. SAM 3 vs SAM 3.1 Relevant Differences｜與本題相關的差異

本次 SAM 3 路徑未使用 SAM 3.1 的 Object Multiplex。官方 [SAM 3.1 發行說明](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)描述多物件共用記憶的加速變更；本題關鍵仍是單一已知實體手機的安全延續。SAM 3 的 box 視覺示例可能回傳多物件，故主臂在**提示影格**用與凍結 YOLO 框的交集挑定一個局部 ID，之後不依評分標籤改選。補充 point 臂則把同一框中心轉為一個正點、固定局部 ID=1，兩者提示語意不同，數字分開列示。

## 7. Environment｜環境

Windows 11、RTX 5070 Ti 16 GiB；獨立 `.venv_sam3` 使用 Python 3.12.8、PyTorch 2.10.0+cu128、`triton-windows`，未安裝 FlashAttention 3。SAM 2.1 使用既有小型 Hiera 權重；SAM 3 官方權重大小 3,450,062,241 bytes。完整版本和 GPU 紀錄在 [environment_manifest.json](environment_manifest.json)。

## 8. Stage A Runtime Feasibility｜短測條件

固定 test8 f804、810、816、822、828、834、840、846 八個影格與同一凍結 YOLO 框 `[529.422,466.482,660.660,594.860]`。預先設定通過條件：選定目標非空至少 6/8、傳播小於 30 秒、保留 GPU 記憶小於 14 GiB、真正執行注意力且輸出可靠。實測兩臂均為 8/8 非空；SAM 3 box 在提示時產生局部 ID 0、1、2，選定 ID 2。短測只證明路徑可用，**不推定物理身分正確**。[原始結果](stage_a_feasibility.json)

## 9. Attention Backend Result｜實際執行路徑

Profiler 觀察到 `aten::_scaled_dot_product_efficient_attention`，本次記錄為 **PyTorch memory-efficient SDPA**；沒有把已安裝套件或原始碼分支當成實際執行證據。SAM 3.1 先前的 Flash／數學後備失敗不可套用到 SAM 3。

## 10. SAM2.1 Smoke Result｜對照短測

同八影格非空 **8/8**；傳播 **1.039 秒**；峰值配置 **726,415,360 B**、保留 **861,929,472 B**（約 0.803 GiB）。

## 11. SAM3 Smoke Result｜SAM 3 短測

同八影格所選 ID 非空 **8/8**；傳播 **1.438 秒**；峰值配置 **6,012,385,792 B**、保留 **6,274,678,784 B**（約 5.84 GiB）。即時 `nvidia-smi` 約 7,245 MiB。這是可運行的短測結果，不是長視窗品質結果。

## 12. Stage A Decision｜階段判定

**PASS**：所有預設可行性門檻滿足，因此按規則執行七片 Stage B。沒有以 V2.6.1 的失敗阻止 SAM 3 實測。

## 13. Seven-Video A/B Method｜七片方法

每支影片的相同窗口、取樣影格、凍結偵測框與允許重新初始化事件，各跑 **SAM 2.1 對照**、**SAM 3 box 主臂**、**SAM 3 point 補充臂**。推論程式不讀人工標籤；三臂的 21 個預測 JSON 與 3,339 個遮罩 PNG 共 **3,360** 個檔案，在遮罩視覺審查前以 SHA-256 凍結於 [prediction_manifest.json](prediction_manifest.json)。之後人工檢查 37 個選定檢查點，15 個可確認原目標可見，另 3 個因實體身分或可見性不足不評分。相同 guard 處理各臂。所有品質比率使用可確認的實體目標，而非非空遮罩率。原始數據見 [comparison_summary.json](comparison_summary.json)。

## 14. Per-Video Results｜逐片結果

表中 `正確／部分／丟失` 的分母是該片已確認目標可見的檢查點；「非空」是所有取樣影格的遮罩計數，**不代表正確**。漂移另在可確認目標不在畫面的檢查點計算。

| 影片 | 可見檢查點 | SAM 2.1 正／部／失 | SAM 3 box 正／部／失 | SAM 3 point 正／部／失 | 取樣影格 | 非空遮罩 2.1／box／point | 已接受漂移 2.1／box／point |
|---|---:|---:|---:|---:|---:|---:|---:|
| test3 | 1 | 1／0／0 | 0／0／1 | 1／0／0 | 157 | 48／0／48 | 0／0／0 |
| test4 | 2 | 0／1／1 | 0／0／2 | 0／1／1 | 159 | 44／0／59 | 0／0／0 |
| test5 | 1 | 1／0／0 | 0／0／1 | 1／0／0 | 171 | 61／0／61 | 0／0／0 |
| test6 | 1 | 1／0／0 | 0／0／1 | 1／0／0 | 132 | 36／0／65 | 0／0／1 |
| test7 | 3 | 1／0／2 | 0／0／3 | 3／0／0 | 185 | 38／0／89 | 0／0／1 |
| test8 | 6 | 5／1／0 | 0／0／6 | 2／4／0 | 200 | 68／0／69 | 0／0／0 |
| test9 | 1 | 1／0／0 | 0／0／1 | 1／0／0 | 109 | 59／0／61 | 1／0／1 |
| **合計** | **15** | **10／2／3** | **0／0／15** | **9／5／1** | **1,113** | **354／0／452** | **1／0／3** |

逐片 [test3](test3/review.md)、[test4](test4/review.md)、[test5](test5/review.md)、[test6](test6/review.md)、[test7](test7/review.md)、[test8](test8/review.md)、[test9](test9/review.md) 審查表列出每個影格的標籤和理由。

## 15. Correct-Target Coverage｜正確目標覆蓋

SAM 2.1 **10/15（66.7%）**、SAM 3 box **0/15（0%）**、SAM 3 point **9/15（60.0%）**。若寬鬆把部分遮罩也算作碰到目標，分別為 **12/15、0/15、14/15**；但 point 在 test8 的手部外溢與細小殘片不能當作完整正確。box 主臂長視窗 **0/1,113** 非空，與短測 8/8 的反差應視為本次整合設定在長序列上的失效；不能據此宣稱官方 SAM 3 在所有提示或環境都失效。

針對 test8 的 50 個取樣影格另做**不改動已凍結預測**的重現診斷：提示當下仍產生三個局部 ID，遮罩面積為 3,844／5,276／11,383 像素；開始長視窗傳播後，前八影格的輸出 ID 清單全部為空。故此次全空不只是挑錯局部 ID 或遮罩寫檔的問題；根因仍待分析。[診斷 JSON](smoke/sam3_box_long_window_diagnostic.json)

## 16. Drift｜錯物件漂移

37 個審查點中，SAM 2.1 **1** 次原始漂移、**0** 次 guard 擋下、**1** 次 guard 接受；SAM 3 box **0／0／0**，但其全空輸出不構成安全優勢；SAM 3 point **3／0／3**。test6 f732 point 落在手邊、test7 f948 落在手／玩偶邊緣、test9 f978 兩個非空臂落在玩偶底座旁，當時原目標均不可見。這些漂移**沒有**計入正確覆蓋。這是選定檢查點中的事件數，不是全 1,113 幀的人工漂移普查。

## 17. YOLO-Gap Recovery｜無偵測機會

已確認目標可見的審查點中，可核對「YOLO 未偵測原目標」的機會為 **0/15**，因此三臂恢復數皆 **0/0，無法估計成功率**。尤其 test8 f852、f864 的紅框是**室內電話干擾物**，畫面左側的原智慧型手機仍被 YOLO 偵測並由部分 SAM 遮罩追蹤，不能把它們當作 YOLO-gap 救援。此指標仍需專門標註的目標可見且 YOLO 漏檢影格。

## 18. Occlusion / Viewpoint｜遮擋與視角

test4 f216 的手機被手壓住，兩個非空臂遮罩均包含手，標為部分；f1038 原手機清楚放在桌上，但三臂皆失去。test5 f438 的細線遮罩落在紙箱邊緣，無法從該單幀確定實體手機，故不列成功或漂移。test9 f762 桌下的小遮罩也因身分不明而排除。這些保守判斷避免以外觀相近物或遮罩面積取代實體身分。

## 19. Test7 Safety｜候選安全邊界

f636 可見的室內電話是 V2.6 `PROVISIONAL_MATCH` 干擾物；**SAM 2.1、SAM 3 box、SAM 3 point 均未在此重新初始化 `phone_01`**。f708、f834 已審查為原目標智慧型手機在手中：SAM 2.1 和 box 均空，point 兩次正確（point **2/2**，其餘 **0/2**）。f948 的 point 遮罩漂至手／玩偶邊緣且被 guard 接受，顯示延續收益伴隨身分安全問題。

## 20. Test8 Post-ReID｜確認後延續

f804 `CONFIRMED_MATCH` 合法重新初始化同一 `phone_01`。在 f804、840、852、864、900 五個已確認原目標可見的後續檢查點，SAM 2.1 **4/5 完整正確、1/5 部分**；SAM 3 box **0/5**；SAM 3 point **1/5 完整正確、4/5 部分**。point 在 f804、840 包含大量手部，f864 只剩原手機邊緣。f852、864 的 V2.6 干擾物標籤指右側室內電話；SAM 2.1 及 point 遮罩位於左側原智慧型手機，**不是**漂移到該干擾物。f1002 遠方有人拿手機，但無法確認是否同一實體，未進入分母。

## 21. Runtime / VRAM｜代價

七片相同 **1,113** 個取樣影格的傳播時間合計：SAM 2.1 **57.791 秒、19.26 sampled FPS**；SAM 3 box **213.490 秒、5.21 sampled FPS**；SAM 3 point **226.428 秒、4.92 sampled FPS**。box 約為對照的 **3.69 倍**傳播時間，point 約 **3.92 倍**。跨窗口峰值 CUDA 保留記憶：2.1 **864,026,624 B（0.805 GiB）**、box **7,600,078,848 B（7.08 GiB）**、point **7,616,856,064 B（7.09 GiB）**。FPS 是取樣影格數除傳播時間，**不含**影片抽幀、模型載入、提示、寫檔及整條 FindMind pipeline。

## 22. Visual Comparison｜圖像證據

每片有四欄原圖／SAM 2.1／SAM 3 box／SAM 3 point 的 [test7 對照圖](test7/sam21_vs_sam3_contact_sheet.png) 和 [test8 對照圖](test8/sam21_vs_sam3_contact_sheet.png)，以及各片時間線。例如 [test7 f708 放大](test7/candidate_zoom/f000708.png)清楚顯示 point 找回原手機；[test8 f852 放大](test8/candidate_zoom/f000852.png)顯示紅框室內電話為干擾物，兩個非空遮罩在左方原智慧型手機；[test4 f1038 放大](test4/candidate_zoom/f001038.png)顯示三臂均漏掉桌上原手機。圖中「guard ACCEPT」只表示現有 guard 接受遮罩，**不等於物理身分正確**。

## 23. Limitations｜限制與可重現性

- 37 個選定檢查點中只有 15 個確定原目標可見，並無逐影格真值或 IoU 密集標註；比率不可外推為整支影片準確率。3 個身分不明檢查點排除。
- 本次預測在 V2.6.2 遮罩審查前凍結，推論程式不讀標籤；但操作人員**曾在凍結前閱讀既有 V2.6 review notes**，所以不聲稱嚴格的人員盲測。程式凍結與人工盲性分開記錄。
- SAM 3 box 短測成功、長視窗全空；額外診斷排除了單純選錯局部 ID，但原因尚未定位，可能與視覺示例或長序列處理有關。結論僅適用本次固定設定，需進一步追查官方推論狀態才可歸因。
- SAM 3 point 是額外診斷臂，不是與 SAM 2.1 同形式 box 提示的嚴格單變量比較；其收益不可直接轉述為主臂勝出。
- 已確認可見檢查點無 YOLO-gap，不能評估漏檢救援。採樣 FPS 不是產品即時 FPS。
- 18 項 V2.6.2 回歸測試通過。影片輸入雜湊、模型版本、窗口、預測凍結和逐片審查均存放於本資料夾以供覆核。

## 24. Recommendation｜決策

**`KEEP_SAM21`。** SAM 3 官方權重和快速注意力路徑在此硬體上可用，但本次 box 主臂七片無有效遮罩；point 補充臂雖在 test7 f708／f834 補上對照遺失的原手機，整體完整正確仍低於 SAM 2.1（**9/15 對 10/15**），已接受錯物件漂移更多（**3 對 1**），傳播較慢且峰值記憶約為 **7.09 GiB**。依 FindMind 優先次序「同一實體正確、低漂移、延續、漏檢救援、速度」，目前沒有採用 SAM 3 的證據。

下一步可在**不改變目前原型**下，繼續 Spatial Memory Graph；研究線單獨診斷 box 長視窗全空的原因，並先修補 point 遮罩的身分安全，再以更密的真值和真正 YOLO-gap 影格重測。機器可讀決策見 [recommendation.json](recommendation.json)。
