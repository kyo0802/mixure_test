# V2.1 實測、瓶頸診斷與 SAM 3 決策

日期：2026-09-23。輸入 `test1.mp4`、`test2.mp4`；原模型 Qwen2.5-VL-7B-Instruct、NF4 4-bit/BF16、RTX 5070 Ti。沒有更換 detector/tracker/VLM，也沒有實作 SAM。完整命令見 [README_V21.md](README_V21.md)。

## 1. Architecture changes

新增獨立 `v21` 模組，569 個 baseline 中的既有 V1/V2 程式、設定、測試與 V2 成果 hash 全部不變。V2.1 先對全部可用 local tracklets 做 quality 與 persistent identity，再沿用 V2 事件及語意分析。GT 僅在 evaluator CLI 讀取；事前 prediction manifest 防止評估改寫預測。未用 GT 改 threshold、合併、命名、事件選擇或 prompts。

Resolver 輸出 MATCH／AMBIGUOUS／NEW_ENTITY，以外觀 histogram、短時間連續、位置、motion、area ratio 多線索決策，同時可見禁止合併，同類別不足以合併。這是保守 hypothesis，不是物理 identity 真值。VISIBLE／UNOBSERVED／LOST 保存最後確認時間與 bbox，缺觀測不補 current bbox。未知類別仍可有 persistent ID。

新增 16 次真實 GPU persistent-context 推論，三相位場景＋歷史 crop＋ID 映射，允許 NONE／UNCERTAIN。V2 舊語意結果使用驗證過的 cache；新增呼叫無 cache hits。Observation graph 與 physical memory 分離，IMAGE_* 永不自動提升物理關係。

完整回歸 **65 passed**，包含零事件預算仍保留身份、同時可見物件不合併、ambiguous、缺失不補bbox、GT隔離、漏偵測不誤算association、負例合併，以及必要before-visible crop不被額外context預算排擠。歷史crop上限384px，場景圖沿用960px；GPU同時被其他程式使用時曾顯著變慢，這次耗時不能作為模型純效能benchmark。

| Inference 結果 | task1 | task2 |
|---|---:|---:|
| local tracks | 77 | 96 |
| usable identity tracklets | 64 | 77 |
| persistent hypotheses | 62 | 76 |
| MATCH / AMBIGUOUS | 2 / 1 | 1 / 1 |
| 新增 GPU context 呼叫 / schema valid | 8 / 6 | 8 / 8 |
| observation relations | 90 | 82 |
| physical candidates / promoted | 8 / 0 | 11 / 0 |
| V2 counterfactual usable-track admission loss | 20 | 35 |
| V2.1 usable tracks 在 identity 前被 event admission 移除 | 0 | 0 |
| 本次推論耗時（含渲染、cache reuse） | 727.3s | 132.8s |

耗時不含模型下載，不是 SAM 比較或純 GPU 吞吐 benchmark。

## 2. Task1 results

Detection：手機 8 個人工確認可見樣本中，6 個有相符原始偵測，recall **75%**；2 個漏偵測。這只描述特意選出的診斷樣本。

Tracking：track17 最後 observation 在 frame348／11.605s。frame360、384、396（12.006、12.806、13.206s）仍有有效 cell-phone detection，卻沒有對應 local observation。這是 local tracking 證據損失，不能歸咎 resolver。最後人工核對的有效 raw phone detection 是 frame396；frame408／13.606s 可見但漏偵測。精確全片終止時刻仍需更密集 GT。

Association：沒有另一段已驗證 usable smartphone tracklet 可接，smartphone association recovery **NOT MEASURABLE FROM CURRENT GT**。沒有要求最終消失後重新出現。系統兩次 MATCH 不是手機成功重連的證據。

Semantics：track17 phone、track23 basketball 與人工檢視一致；track25 綠色垃圾桶仍 cup，correction 失敗。

Relations：VLM 新回覆有錯誤角色／ID 對應，例如 evt_017 把phone17作為TOUCHING的subject、hand37作為object，說明卻是手碰手機。留在候選，不入物理記憶。evt_019／evt_034只輸出不完整JSON fence而驗證失敗，原文保留；其餘6個新context回覆有效，共8個候選、0 promoted，不能宣稱成功還原拿起／放置。

## 3. Task2 results

Detection：手機 17 個確認可見樣本中，11 個有原始偵測，**64.7%**；6 個漏偵測。另有 1 個抽查籃球樣本漏偵測。玩偶旁手機不是整段「完全沒有 raw detection」：17.607s、18.607s、19.808s 有間歇性 cell-phone boxes，這是對敘事描述的逐影格細化，未修改 inference。

Tracking：原手機 track22（2.60–4.00s）→track43（4.80–9.60s）是人工可辨識的同一手機；之後五個抽查手機樣本有 raw detection 卻無 local observation，包含上面的三個玩偶區 raw hits。最後 local phone track observation 在 frame288／9.604s；最後人工核對 raw phone detection 在 frame594／19.808s。20.008s 可見極小邊缘但不確定，排除 recall；20.408s 之後檢視樣本被遮住，不算漏偵測。

Association：人工確認的兩對可關聯 fragments 中，78→81（同一左桌機）成功；22→43（原手機）失敗，**1/2 = 50%**，樣本極小。22→43 gap0.80s、appearance0.898，但畫面位移0.219、motion error0.403 不過事先固定 gate；保留分離，未以 GT 放寬門檻。尚無 camera-motion compensation。

Admission：人工確認有用的 track41（綠垃圾桶短段）、track80（右桌機）在 V2 被移除，V2.1 都保留身份。但保留身份不代表已有正確語意：41 仍 unknown。

Semantics／relations：籃球17正確、手機43為phone；22／41 unknown。另有椅子track4被誤標flip-flop。物理 candidate11，promoted0。

## 4. Smartphone trajectory analysis

![Task1 sparse diagnostic](outputs_v21/task1/gt_review/smartphone_diagnostic_timeline.png)

![Task2 sparse diagnostic](outputs_v21/task2/gt_review/smartphone_diagnostic_timeline.png)

三列分別為人工可見性、raw detection、local observation。紅點是確認可見樣本的該層缺失；灰點為遮擋／出畫／不確定而排除。點間空白不是連續真值，也未內插。敘事 GT 的完整移動路徑只在 evaluation 保存；沒有把「放到籃球／玩偶後」寫入 VLM prompt。

historical context 必須保留before-visible但後續漏偵測的supplied物件，另外補入最近四秒內最多兩個未觀測references。task2手機local track在9.60s結束，與最終放置相隔很久，不能保證該手機仍進入19.8s事件上下文。這是有限上下文與上游觀測缺失的實際限制，沒有宣稱V2.1已解決整段軌跡。

## 5. False-merge tests

人工 mapping 上，task1 檢查原手機≠後段桌機與兩張不同椅子，共2對；task2 檢查原手機≠兩支桌機、兩支桌機互異、兩張不同白椅，共4對。**6個可評估 distinct pairs，false_merge_count=0**。不代表所有62／76個 hypotheses 都已驗證無誤，也不把相似椅子的碎片數當成實際椅子數。

task2 tracks78/81 是同一左桌機；track80 是同時可見的另一支，沒有為提高 recovery 把三種電話合在一起。task1 後段畫面還能看到其他桌機，提供的 narrative 只指定一個 desk_phone_01，本次不憑敘事虛構其餘全片身份標註。

## 6. Spatial-memory tests

task1 的90個、task2的82個 image-plane observations 留在 observation graph。兩片各兩個 trash-bin NOT physically NEAR 的負例都沒有違規 promotion。物理圖沒有強行把近的投影框寫成 physical NEAR。

本次 physical memory 邊數為0，因此負例通過有保守拒絕／空圖效應，不能據此宣稱理解真實距離，也不能估算 relation recall。尤其 task2 短垃圾桶 track 未必參與 selected event，不能把沒有邊當成成功推理。

## 7. Error attribution

下表混合「抽查影格」、「物件／fragment pair」、「人工語意案例」等證據單位，**不可直接加總成錯誤率或拿最大數目宣稱主要因果**。

| 類型 | task1 | task2 | 解讀 |
|---|---:|---:|---|
| DETECTION_FAILURE | 2 | 7 | task2 = 手機6＋籃球1 |
| CLASSIFICATION_FAILURE | 2 | 1 | raw detection 與已知類別不符 |
| TRACK_FRAGMENTATION | 0 | 1 | 已標註手機出現兩個 local IDs；完整事件數不可量測 |
| ID_SWITCH | 0 | 0 | 抽查未證實；全片 exact count 不可量測 |
| ASSOCIATION_FAILURE | 0 | 1 | task1 不可評 recovery；task2手機22→43 |
| FALSE_MERGE | 0 | 0 | 僅限上述6個distinct pairs |
| ADMISSION_FAILURE | 0 | 2 | V2 counterfactual，V2.1 已保留這些身份 |
| SEMANTIC_REASONING_FAILURE | 1 | 1 | 人工列舉的垃圾桶／椅子誤判案例 |
| RELATION_REASONING_FAILURE | 1 | 0 | task1 候選角色反轉，沒有進最終 memory |
| INSUFFICIENT_EVIDENCE | 3 | 6 | raw detection 有而 local observation 無；task2含5手機＋1垃圾桶 |

上列最後一類的下游 association 證據不足，但其 raw→local 損失屬 LOCAL_TRACKING_LIMITED 證據，保存在獨立 `raw_detections_without_local_track_on_reviewed_samples` 欄位，不假裝已知 ByteTrack 內部精確原因。抽查 track purity 都是1.0，分母很小，只代表已配對樣本沒有跨物件污染；全片 purity、ID switches、完整 fragmentation count 為 **NOT MEASURABLE FROM CURRENT GT**。

## 8. Bottleneck diagnosis

兩片均為 **MIXED**。task1 有 detector miss、raw detection 未成 local track、語意錯誤；task2 另有可用 phone fragments 未重連，以及 V2 admission 丟失重要短track的對照證據。V2.1 解除了 event admission 對 identity 的刪除，但不能創造不存在的 observations，也未恢復所有 association。

目前不能只稱 ASSOCIATION_LIMITED，也不能只稱 DETECTION_LIMITED。camera motion、手遮擋、可見部分變小可能共同影響 detector與局部追蹤；沒有用這些推測取代 GT 指標。

## 9. Segmentation-propagation decision

**不建議現在把 YOLO＋VLM 整套換成 SAM 3；建議下一步做受控 segmentation propagation A/B。** 理由是已看到可見手機重複漏偵測，以及 raw boxes 存在卻未形成 local track，後端 resolver 無法回收不存在的 tracklet。這是測試局部 continuation 表示的實證理由，並非 SAM 已勝出。

SAM 3 官方定義為可透過 text／visual prompts 偵測、分割並追蹤影像或影片物件；它不是這套 VLM interaction reasoning／memory promotion 的直接替代品。[官方 repository](https://github.com/facebookresearch/sam3)、[官方論文](https://arxiv.org/abs/2511.16719)。截至本次檢查官方 repo 已提供 SAM3.1；實驗必須預先固定 SAM3 或3.1 checkpoint／code revision，不能混用名稱與結果。

| 控制項 | A | B |
|---|---|---|
| 初始化 | 固定的原始 YOLO detections | 同一組 YOLO初始化 boxes |
| 後續局部表示 | 現有 local tracker | SAM temporal mask propagation，轉出相容 observations |
| 其餘 | 固定 resolver、events、同一7B VLM、evaluator、graph與memory rules | 完全相同 |

分開測「已正確初始化後的可見性延續」與「初始化本來就沒有 detection」。不得給B一個GT box而A沒有。若另外測 SAM text detector，作第三個獨立實驗，固定同等 prompt vocabulary，禁止輸入 GT 路徑／隱藏目的地。

比較 visibility-conditioned coverage、fragmentation、ID switches、purity、association recovery、false merges；同時量測 GPU memory、吞吐與額外 false positives。先補密集review intervals／一對一匹配標註，再評估A/B顯著差異。物理 relation與語意指標繼續單獨評估，不能期待 mask 自動解決它們。

R4DSG-inspired 僅指 persistent association／時間記憶原則；沒有重現其完整4D管線或3D evidence。[R4DSG論文](https://arxiv.org/abs/2608.11017)。

## 10. Remaining uncertainty and evidence

- User narrative GT：原手機最終不再出現、不同桌機不是原手機、垃圾桶物理上不近；僅用於評估。
- Assistant manually reviewed：保存在evaluation JSON的框、可見性、選定track contact sheets與distinct pairs；不是人類標註員的密集benchmark。
- System inferred：62／76身份假設、quality flags、VLM interpretations、候選關係；仍可能錯。
- Not measurable：全片recall／purity／exact ID switches、task1 smartphone recovery、全片false-merge rate、SAM改善幅度。

GT annotations 是非隨機稀疏樣本；IoU≥0.3且框為可見部分近似界線，分母小、定位有人工誤差。沒有以GT改善模型參數再回報同一組評分。Promotion要求多事件支持可能壓低relation recall，待更多獨立資料驗證。

證據：[task1 validation](outputs_v21/task1/validation_report.md)、[task2 validation](outputs_v21/task2/validation_report.md)、[稽核](docs/v21_artifact_audit.json)、[task1 annotations](evaluation/v21/task1_annotations.json)、[task2 annotations](evaluation/v21/task2_annotations.json)。完整錯誤與分母在各輸出的error_analysis.json；模型原文與prompt在event_analysis/events下。

