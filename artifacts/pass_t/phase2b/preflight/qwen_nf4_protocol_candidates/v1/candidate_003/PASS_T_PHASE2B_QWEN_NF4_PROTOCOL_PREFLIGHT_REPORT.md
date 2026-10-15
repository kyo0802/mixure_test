# FindMind Pass T Phase2b Qwen NF4 離線預檢報告

`PASS_T_PHASE2B_QWEN_NF4_PREFLIGHT_COMPLETE_AWAITING_USER_PROTOCOL_DECISIONS`

`PROTOCOL_NOT_READY_TO_FREEZE`。本次 VLM 載入／推論／smoke重跑／計分／freeze／Graph／commit／push 均為0。

## 1. 查證結果

Dataset獨立SHA核對：`ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c`。原policy、A/B sidecar、negative readiness與eligibility均保留。歷史Qwen有效NF4 double/BF16/SDPA是實測，當前長視窗可執行性仍未驗證。

| Property | Verified value | Source / field | Level | Limitation |
|---|---|---|---|---|
| model | "Qwen/Qwen2.5-VL-7B-Instruct" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.model | REAL_RUNTIME_VERIFIED | Historical synthetic execution only; not current DEV capacity |
| revision | "cc594898137f460bfe9f0759e9844b3ce807cfb5" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.revision | REAL_RUNTIME_VERIFIED | Historical synthetic execution only; not current DEV capacity |
| model_load_seconds | 20.442865599994548 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.model_load_seconds | REAL_RUNTIME_VERIFIED | Historical synthetic execution only; not current DEV capacity |
| model_load_peak_vram_bytes | 7241465856 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.model_load_peak_vram_bytes | REAL_RUNTIME_VERIFIED | Historical synthetic execution only; not current DEV capacity |
| quantization_config | {"_load_in_4bit": true, "_load_in_8bit": false, "bnb_4bit_compute_dtype": "bfloat16", "bnb_4bit_quant_storage": "uint8", "bnb_4bit_quant_type": "nf4", "bnb_4bit_use_double_quant": true, "llm_int8_enable_fp32_cpu_offload": false, "llm_int8_has_fp16_weight": false, "llm_int8_skip_modules": null, "llm_int8_threshold": 6.0, "load_in_4bit": true, "load_in_8bit": false, "quant_method": "bitsandbytes"} | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.quantization_config | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| attention | "sdpa" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.attention | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| device_map | {"": "cuda"} | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.device_map | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| cpu_offload | false | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.cpu_offload | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| bitsandbytes_version | "0.50.2" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.bitsandbytes_version | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| torch_version | "2.10.0+cu128" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.torch_version | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| cuda_runtime | "12.8" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.cuda_runtime | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| transformers_version | "4.57.6" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.transformers_version | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| processor | {"_processor_class": "Qwen2_5_VLProcessor", "crop_size": null, "data_format": "channels_first", "default_to_square": true, "device": null, "disable_grouping": null, "do_center_crop": null, "do_convert_rgb": true, "do_normalize": true, "do_pad": null, "do_rescale": true, "do_resize": true, "image_mean": [0.48145466, 0.4578275, 0.40821073], "image_processor_type": "Qwen2VLImageProcessorFast", "image_std": [0.26862954, 0.26130258, 0.27577711], "input_data_format": null, "max_pixels": 200704, "merge_size": 2, "min_pixels": 3136, "pad_size": null, "patch_size": 14, "resample": 3, "rescale_factor": 0.00392156862745098, "return_tensors": null, "size": {"longest_edge": 12845056, "shortest_edge": 3136}, "temporal_patch_size": 2} | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: health.effective_runtime.processor | REAL_RUNTIME_VERIFIED | Historical effective configuration; image fast max_pixels and size fields may conflict, measure CPU behavior |
| generated_tokens | 179 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].resource_receipt.generated_tokens | REAL_RUNTIME_VERIFIED | Allocation/end snapshot is not global GPU peak; no separate prefill timing |
| runtime_seconds | 49.34192489999987 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].resource_receipt.runtime_seconds | REAL_RUNTIME_VERIFIED | Allocation/end snapshot is not global GPU peak; no separate prefill timing |
| peak_inference_vram_bytes | 6304462336 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].resource_receipt.peak_inference_vram_bytes | REAL_RUNTIME_VERIFIED | Allocation/end snapshot is not global GPU peak; no separate prefill timing |
| peak_reserved_bytes | 7354712064 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].resource_receipt.peak_reserved_bytes | REAL_RUNTIME_VERIFIED | Allocation/end snapshot is not global GPU peak; no separate prefill timing |
| gpu_free_total_bytes | [8326742016, 17066033152] | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].resource_receipt.gpu_free_total_bytes | REAL_RUNTIME_VERIFIED | Allocation/end snapshot is not global GPU peak; no separate prefill timing |
| processor_grid_thw | [[1, 16, 16]] | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].resource_receipt.processor_grid_thw | REAL_RUNTIME_VERIFIED | Allocation/end snapshot is not global GPU peak; no separate prefill timing |
| Strict JSON and citations | {"citation_errors": [], "semantic_errors": [], "structural_errors": [], "valid": true} | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: records[0].validation | RECEIPT_VERIFIED | No visual correctness or event accuracy claim |
| EOS | "NOT_VERIFIED" | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\smoke_results\8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0\summary.json :: EOS field absent | NOT_VERIFIED | 179 < 512 and complete JSON does not prove EOS |
| response_format_system | "Respond with exactly one compact JSON object conforming to the user supplied schema. Begin with { and end with }. Do not use Markdown fences or prose outside JSON. Keep rationale and uncertainty strings short; do not copy the schema into the response." | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\deployment.json :: response_format_system | CONFIG_DECLARED | Synthetic configuration is not approved real-window protocol |
| generation_timeout_seconds | 180 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\deployment.json :: generation_timeout_seconds | CONFIG_DECLARED | Synthetic configuration is not approved real-window protocol |
| max_images | 3 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\deployment.json :: max_images | CONFIG_DECLARED | Synthetic configuration is not approved real-window protocol |
| max_frames | 8 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\deployment.json :: max_frames | CONFIG_DECLARED | Synthetic configuration is not approved real-window protocol |
| processor_max_pixels | 200704 | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\deployment.json :: processor_max_pixels | CONFIG_DECLARED | Synthetic configuration is not approved real-window protocol |
| synthetic_only | true | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\deployment.json :: synthetic_only | CONFIG_DECLARED | Synthetic configuration is not approved real-window protocol |
| Generation configuration | {"max_output_tokens": 512, "sampling": false, "seed": 42, "temperature": 0.0} | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\prepared\02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8\config.json :: generation | CONFIG_DECLARED | Greedy temperature may be ignored; seed not determinism guarantee |
| Local file integrity | {"chat_template.json": "ad60d90252ed0b0705ba14e2d0ad0fec0beac1ea955642b54059b36052d8bc96", "config.json": "77d9ec7321cc572e3579e2c84799c9cadaded63c49ce93b101733349fc330c43", "download_provenance.json": "262283e6e7dffaf1e76c27f7d630e5e5ddc55db8c5f433f9fd19df05f00077e2", "generation_config.json": "0a3aea82869fe29f20dc95ccf3e2bcff380eca1f5ad6447a4a4b37110b08e43e", "merges.txt": "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3", "model-00001-of-00005.safetensors": "e97b877e47fde53a6c6e77aafb36e58e91ee9d95c4a3eeac6f1b5c0e6a1c986e", "model-00002-of-00005.safetensors": "a9a300a43b4724eee2abe7c18ceb26768d0ab011eb0cad19d9bfd2476a24d024", "model-00003-of-00005.safetensors": "111223d173e00bbee81cba1216fad28668df3476706b7fd26f4d5b50f8b3a507", "model-00004-of-00005.safetensors": "ef47f634fa57d46ee134edcc09f34085a47da1e16c12a2abe0d67118be6d72ed", "model-00005-of-00005.safetensors": "0c859795ad3a627a9b95bcb762e059d5b768a4a36fdd4affeff269d93fdecc67", "model.safetensors.index.json": "73b333b0b16e5286ddba615d2caebcd495cf7e616f52eb217a81781393d79de9", "preprocessor_config.json": "f2058c716eef96ccaed1cc1e2d0c08306b62586d535b28d9d08e691b2fab7ca0", "tokenizer.json": "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539", "tokenizer_config.json": "4abd3520120e266da84c0864fee064d1fb10806f02225911a47253dd38dc5f56", "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"} | artifacts\pass_t\phase2b\local_runtime\qwen_nf4\asset_audits\3dcbc1f0a680104e0beb27366691f9e68b5b88a4e8df354c67da0ff3c2a6cf57\assets.json :: files_sha256 | RECEIPT_VERIFIED | Rehashed in current preservation; upstream checksum unavailable |
| Revision authority | "local download provenance" | .models\Qwen2.5-VL-7B-Instruct\download_provenance.json :: revision | RECEIPT_VERIFIED | Pinned provenance != independent official checksum attestation |
| Video system instruction | "NOT_APPLIED_IN_EXISTING_VIDEO_PATH" | src\memory_graph\pass_t\phase2b\local_vlm\nf4.py :: generate_video conversation | STATIC_CODE_VERIFIED | Current video ignores V2 system, seed and envelope do_sample; future parity adapter required |

## 2. 取樣比較

| Policy | Observed max-gap range s | No event-recognition guarantee |
|---|---|---|
| UNIFORM_3 | 1.200000–1.953333 | NOT_ESTABLISHED |
| UNIFORM_8 | 0.366667–0.568333 | NOT_ESTABLISHED |
| UNIFORM_12 | 0.233333–0.368333 | NOT_ESTABLISHED |
| UNIFORM_16 | 0.166667–0.268333 | NOT_ESTABLISHED |
| FIXED_FPS_4 | 0.266667–0.268333 | NOT_ESTABLISHED |

六窗各五種取樣，原始native PTS與完整native IDs／gap表見 temporal sampling report。沒有d_min、沒有跑GT-informed diagnostic、没有GT event-time offset。

## 3. 參考圖

五窗有human-authorized既有窗前reference，test1沒有；model-use授權仍待本次protocol選擇。推薦先批准一致neutral target定位方案，或五窗static與test1 NONE分開解讀；不能把NONE默認為主條件或混合結果。

## 4. 離線輸入與預處理

66候選package：60 multi/storyboard＋6完整授權video。所有video decoded pixels逐張核對；private provenance與opaque model-visible資產分離。CPU processor observations：66 verified；原6個video template失敗保留，另存6個CPU-only修正成功紀錄。產物統計截至報告生成前：834 files / 668926603 bytes（最終含報告/receipt總數見offline_candidate_receipt，避免循環自雜湊）。candidate001缺Image import、candidate002舊scanner誤判允許的native PTS；失敗產物保留，未改原core。

## 5. Leakage

結構allowlist/metadata/source邊界通過；像素語意和video container完整blinding仍UNABLE_TO_DETERMINE，不能宣稱完整PASS。六張uniform8 contact sheet直接檢視記錄見visual_inspection.md。未使用GT bbox或答案overlay。

## 6. Runtime限制

CPU acceptance不證明GPU容量／生成成功。實測video937664pixels/frame超過宣告200704；五窗14張、最短8張，六窗最後endpoint均未選。Video引用須限制實際processed aliases；原video未套V2 system，與影像不對稱。本次沒改runtime。Actual container PTS另存，FFV1 FPS有rounding，不能把nominal mapping當exact容器時間。历史EOS欄位缺失、没有新global GPU peak/CPU RSS/prefill分項；長窗不能借用smoke資源。RUNTIME_NOT_VERIFIED；見VIDEO_PROCESSOR_OBSERVATIONS.md。

## 7. 建議參數（未核准）

Uniform8作探索折衷；3欄storyboard；full-rate FFV1 video＋processor4fps；greedy/repeat1；output1024、generation300s/request330s、retry0generation；固定共同0.2s容差仍需task justification與明確批准。先做形狀一致synthetic容量probe；這只是設計，本次未執行。

## 8. 人工決策

請以QWEN_NF4_PROTOCOL_DECISION_SHEET.md逐列決定22項。主要阻擋為：reference授權及跨窗對稱、video prompt parity、effective像素budget、容量證據、時間容差依據與完整人工批准。Prompt components draft SHA：`187f59fd1c85284c6ae33894f61761c24b82581687794a16cf3556772de653ff`；draft protocol SHA：`a91296147e184c608945bb328fd6802a2b89619e85f801ea56f030d4bc3281fd`。這不是approved freeze hash。

## 9. 保存與測試

[
  {
    "file": "new_final_42_junit.xml",
    "attempt": "FINAL",
    "tests": 42,
    "failures": 0,
    "errors": 0,
    "skipped": 0
  },
  {
    "file": "new_final_junit.xml",
    "attempt": "FINAL",
    "tests": 40,
    "failures": 0,
    "errors": 0,
    "skipped": 0
  },
  {
    "file": "new_junit.xml",
    "attempt": "INITIAL_RETAINED",
    "tests": 40,
    "failures": 1,
    "errors": 0,
    "skipped": 0
  },
  {
    "file": "regression_final_junit.xml",
    "attempt": "FINAL",
    "tests": 16,
    "failures": 0,
    "errors": 0,
    "skipped": 0
  },
  {
    "file": "regression_junit.xml",
    "attempt": "INITIAL_RETAINED",
    "tests": 16,
    "failures": 1,
    "errors": 0,
    "skipped": 0
  }
]

完整protected hash / HEAD / index / tracked diff結果見preservation.json；新候選immutable清單見offline_candidate_receipt.json。既有dirty改動不reset、不stage。全部新產物獨立versionnamespace。

## 10. 下一個授權任務

請先決定reference/sampling/budgets等protocol項目，必要時另授權新matched-shape synthetic容量probe及video formatting parity修補。解決後再交付完整protocol供你批准；未批准不可freeze。未來freeze後仍須另下 `RUN_PHASE2B_EXPLORATORY_PILOT` 才能跑DEV。現有offline build及tests已實際執行；沒有虛構新的probe/freeze指令。

剩餘科學限制：event-expected小樣本、無PLACEMENT/exhaustive positive、非完整事件額外預測UNEVALUATED、負例缺完整獨立視覺複核、session independence與causality未驗證，所有正式accuracy/precision/recall/F1/hallucination率/顯著性/優越性/泛化均UNDEFINED。
