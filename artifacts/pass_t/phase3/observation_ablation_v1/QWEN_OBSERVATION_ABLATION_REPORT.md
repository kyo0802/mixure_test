# Qwen Observation Ablation ＋ Cross-model Preparation

更新：2026-10-17（Asia/Taipei）。結論：**STATE_FIRST_IS_PROMISING**，僅限可讀的狀態觀察訊號；**事件遺漏、過度延伸引用與strict輸出仍未解決，不升為完整Phase 3主流程。**

## 1. 完成範圍

**B兩次＋C兩次＝4/4新Qwen生成完成**，皆正常EOS，未碰token cap／generation deadline；兩worker exit0、無安全門檻停止，重試0、追加生成0。A直接重用10/15既有兩筆，沒有重跑。新模型推論0、權重下載0、安裝／降級套件0；沒有改GT、原始影片、Frozen split、V297、舊實驗或Memory Graph，沒有commit／push。

原始輸出與execution、processor／tensor metadata、strict validation保存在各條件資料夾；[execution_summary.json](execution_summary.json)及[comparison.json](comparison.json)是統整入口。既有CV `PHASE3_SIGNAL_CHECKPOINT_BLOCKED`結果不變。本實驗仍是受已知錯誤啟發的兩個DEV視窗，不是獨立或無偏benchmark。

## 2. A/B/C實際差異

| 項目 | A：歷史baseline | B：Higher detail | C：State-first |
|---|---|---|---|
| 模型／量化 | Qwen2.5-VL-7B-Instruct NF4 | 與A相同 | 與A相同 |
| Source images | 每窗相同8張frozen Uniform8 PNG | 完全相同，順序／alias／native PTS不變 | 完全相同 |
| 表示 | 依時序獨立多圖，非native video | 相同 | 相同 |
| Pixel cap／實際W×H | 200704／588×336 | **401408／840×448** | 200704／588×336 |
| 實際visual tokens／窗 | 2016 | **3840** | 2016 |
| Input tokens／窗 | 3174 | 4998 | 3057 |
| System／task／schema | 原V3 | **與A逐位元相同**，rendered task hash也相同 | System與A相同；task改為先列物件狀態，再可選事件；新精簡schema |
| Decoding | greedy、seed42、max_new_tokens1024 | 完全相同 | 完全相同 |
| 實驗呼叫 | 歷史2筆，不重跑 | 本次2筆 | 本次2筆 |

共同runtime：既有本機 `Qwen/Qwen2.5-VL-7B-Instruct`，revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`，NF4 double quant、BF16 compute、SDPA、CUDA，無CPU offload。使用未修改的shared NF4 loader／generation。Transformer4.57.6、Torch2.10.0+cu128、bitsandbytes0.50.2；沒有constrained decoding。傳入`do_sample=False`，不傳temperature；checkpoint繼承temperature被忽略的警告保存在log。

B實際每圖376320 pixels，是A的197568 pixels約1.90倍；不是完整1280×720，也沒有換成crop／減少影格。C**同時改任務表達與輸出合約**，因此結構完整性的差異不能單獨歸因於視覺推理。

### 前處理修正發生在任何新生成之前

第一次CPU preflight發現僅改processor attributes並未真的提高B尺寸，輸出仍為588×336。已保留 [initial CPU-only紀錄](preflight_initial_cpu_only/cpu_preflight.json)及原程式／freeze；使用processor支援的明確per-call pixel kwargs傳遞B預算，確認B確實840×448後才固定最終設定。沒有改選預算、prompt、schema或decoding，當時新generation為0；不是模型失敗後重試。最終preflight與worker的grid／rendered hash一致。

16張PNG的SHA全部相符，source index與native PTS沿用manifest；沒有近鄰替代、PTS重算或原影片解碼。Runtime沒有讀取人工答案／GT／舊預測作為feature；四筆原文落盤後才讀取人工審閱做質性對照。

## 3. 四次新生成與資源

| 條件／視窗 | Output tokens | 生成秒數 | Torch峰值allocated／reserved GiB | 原始JSON | strict-valid |
|---|---:|---:|---|---|---|
| B／test5 W05 | 314 | 97.34 | 6.537／6.883 | FAIL：Markdown fence | 否 |
| B／test7 W05 | 41 | 2.31 | 6.537／6.883 | FAIL：Markdown fence | 否 |
| C／test5 W05 | 280 | 86.71 | 6.182／6.865 | FAIL：Markdown fence | 否 |
| C／test7 W05 | 237 | 5.92 | 6.182／6.865 | FAIL：Markdown fence | 否 |

B總wall154.88秒、C147.61秒（包含各自載入）；每條件載入同一權重一次，沒有warmup生成。3秒取樣的整卡GPU使用峰值B8.797GiB／C8.773GiB，owned process-tree RSS峰值B4.666GiB／C4.697GiB，均在既有門檻內。取樣不是連續硬體峰值，Torch allocator也不是整張GPU的使用量。各首call與次call長度／快取狀況不同，不把速度差當受控效能結論。

## 4. 同一rubric的語意比較

以下是**報告作者對raw文字／可見影格的質性分析，不是新human adjudication**，更不是獨立CV驗證。

| 維度 | A：既有baseline | B：提高細節 | C：先觀察狀態 |
|---|---|---|---|
| Target | test5寫phone pickup；test7 notes只提phone互動 | test5仍phone；test7沒有操作物描述 | 兩窗均將phone與basketball分開列為觀察物件 |
| State | test5桌面→手持合理；test7沒有狀態對照 | 相同，test7未改善 | **test7寫F0001/F0016 ON_SURFACE、F0031/F0046 HELD_BY_PERSON**；但又延伸至手機不清楚可見的F0062 |
| Temporal references | test5 F0062/F0077有用，F0093遮擋 | test5 F0077有用，F0093仍不確定，未再引用較清楚的F0062 | test5手持延伸到F0047與F0093/F0108欠充分可見支持；test7 F0031/F0046有用，F0062不可外推 |
| Event | test5文字提出PICKUP；test7文字否認 | 與A相同；test7 pickup omission持續 | **兩窗都回NO_CONFIRMED_EVENT，沒有event hypotheses**，卻描述手機狀態變化，觀察與結論不一致 |
| Wrong target | 沒有錯球／card pickup文字 | 沒有錯球／card pickup文字 | 沒有球pickup事件；但部分仍可見桌上球被列UNKNOWN，不能稱為可靠的球狀態辨別 |
| Uncertainty | test5 NONE對遮擋過於肯定；test7未用UNCERTAIN | 問題仍在 | 對球過度棄判、對手機遮擋卻繼續HELD；test5球uncertainty寫state changes亦欠明確支持 |
| Structure | strict0/2 | strict0/2 | strict0/2；body必填完整性有改善，但schema不同 |

**test7的pickup遺漏是否解決？** 事件層沒有：B、C都未產生pickup hypothesis；C只在狀態觀察層恢復了有用的手機桌面／手持描述。不能由程式補一個PICKUP，然後宣稱模型已完成事件推理。

既有人工審閱支持test5 Calls03/10與test7 Call08的physical-event-level pickup，並拒絕Call01的card與Call04的ball attribution。這些舊human reviews未改寫；用來確認本次文字的主要可見脈絡，不轉成新GT或正式FN。test7 F0031/F0046可見手抓握直立手機，C的這兩個state citations有價值；F0062則沒有清楚手機。test5 F0108手機不清楚可見，C不能從更早手持延續填入該格。完整逐案例七維說明見 [comparison.json](comparison.json)。

## 5. Strict validity與受控語意抽取完全分離

六筆A/B/C原文都有Markdown fence；**原始JSON均失敗，schema／citation／semantic strict後續階段均為NOT_EVALUATED，strict-valid各0/2**。沒有修復、填欄位、轉NO_EVENT或修改歷史parsed結果。

本次新增一個明確限定的質性讀取路徑：只有raw完整符合單一外層code fence時，讀取該body的JSON；不搜尋任意substring、不修syntax、不補資料。結果寫在`qualitative_extraction`，標示`authoritative=false`及`changes_strict_validity=false`；**絕不送回strict validation作為原文**。

| 原文 | body可讀後發現的必填缺漏（非原文strict結果） |
|---|---|
| A、B的test5 | 兩個other_objects各缺evidence |
| A、B的test7 | 缺events |
| C的兩窗 | 無必填缺漏；在其NO_CONFIRMED_EVENT合約下events原本可省略，不能誤報為缺欄位 |

C的fenced body能符合較小schema，不表示原文已有效，也不能把改善歸功於狀態推理本身。結構正確、事件正確與引用有物理支持，是三件分開的事。

## 6. RQ與判斷

- **RQ1：沒有看到明確改善。** 在這個約1.90倍實際pixel設定，B未恢復test7手機pickup，test5語意也大致相同。這不能排除更高細節、其他模型或別的視窗有幫助，也不能證明根因完全與視覺細節無關。
- **RQ2：局部觀察訊號值得保留。** C在原budget下說出test7前後手機狀態，但事件推斷、自洽性、遮擋處理與strict格式仍不足。這是**STATE_FIRST_IS_PROMISING**的限定理由，並非C已證明優於其他方法。
- 兩窗、每窗單次生成、已知DEV錯誤、歷史A與新run時間不同、C合約亦改變，都限制因果解讀。沒有accuracy／precision／recall／F1、泛化或完整模型排名；最終仍需另外預註冊held-out比較。

## 7. 跨模型準備與下一步

已新增小型model-neutral [ObservationAdapter介面](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/experiments/observation_interface.py)，支援load／render／preprocess／generate／raw-first capture／resources／close，驗證相同source aliases且不強迫不同模型有相同內部tokens。**4/4 CPU合約測試通過**；只用RecordingAdapter與byte fixtures，並非新模型推論成功。

官方ID、license、輸入與量化／Windows／16GB限制，集中在 [CROSS_MODEL_PREPARATION.md](CROSS_MODEL_PREPARATION.md)：

- `DAMO-NLP-SG/VideoLLaMA3-7B`：有條件的下一候選；官方提供影像／多圖／video與custom Transformers路徑，但本機FlashAttention、量化及16GB容量尚未驗證。[官方model card](https://huggingface.co/DAMO-NLP-SG/VideoLLaMA3-7B)
- `nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16`及官方FP8 variant：模型確實存在；BF16僅權重容量就超過16GiB，且文件的4-image上限／video路徑、Linux／Mamba依賴及FP8輸入限制，都使它不是目前Windows16GB的直接替換品。[官方BF16 card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16)、[FP8 card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-FP8)

**下一個共同任務建議：** 相同8個exact frames，先逐物件列可見物理狀態、source aliases與不確定性；事件hypotheses另列可選項，使用同一七維rubric，原文格式與質性內容分開。不同模型記錄實際tiling／token／temporal mapping，不偷偷重採樣。這是任務提案，不是新prompt已批准，也不等於把C選為已證實較佳的方法。

下一實驗需使用者授權確切模型ID／revision、權重下載、量化與隔離環境變更、共享prompt/schema／輸入路徑及call上限。沒有下載或啟動任何新VLM，也不再追加Qwen試驗。本次到此停止。

## 8. 可追溯紀錄

- 最終freeze SHA：`a80145037f4cb161892abf4125a43ebb6584a27449647a12f9ba94d04d9a16df` — [freeze.json](freeze.json)
- B prompt/schema SHA與A相同；C prompt SHA `ef69002cd66cf61f1448fa741cbf52f4f712d5d7b5ac09fcea0c1d1f1061da1b`，schema SHA `6c929159a5259a82ee9312fe839d3d1cd12fc7bd1cbe8929f730495270599730`。
- [B原始結果及receipt](condition_b_higher_detail)／[C原始結果及receipt](condition_c_state_first)。每筆input記錄包含exact rendered text、source mapping、processor設定、tensor shapes與canonical hashes。
- [verification.json](verification.json)：12/12執行／完整性檢查通過，**563個既有source／report／raw等檔案雜湊未變**；另有3個parser CPU checks及4個interface tests通過，沒有額外真實model calls。
- 新runner：[run_phase3_observation_ablation.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/scripts/run_phase3_observation_ablation.py)。沒有修改shared NF4、舊runner或舊實驗。新介面與測試的source hashes亦列在verification。

VLM的說明仍是自己對事件的主張，不是另一個感測器；本次沒有建立deterministic SUPPORTED Decision、persistent identity、精確事件時間或Graph寫入安全。
