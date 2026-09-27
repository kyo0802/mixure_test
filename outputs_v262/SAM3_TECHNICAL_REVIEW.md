# V2.6.2 官方 SAM 3 技術審查

## OFFICIAL_DOCUMENTATION

- 官方程式庫：[Meta facebookresearch/sam3](https://github.com/facebookresearch/sam3)。目前程式庫同時包含 SAM 3 與 SAM 3.1；兩者的模型建構入口及權重不同。官方 SAM 3 權重來自受存取控制的 [facebook/sam3](https://huggingface.co/facebook/sam3)，檔名 `sam3.pt`。官方程式碼 `download_ckpt_from_hf(version="sam3")` 亦明確選取此檔。
- 官方 README 的最低需求為 Python 3.12、PyTorch 2.7、CUDA 12.6；列出 FlashAttention 3 為**可選**加速套件。README 未承諾 Windows 上所有注意力核心皆可用。本機需實際執行驗證。[來源](https://github.com/facebookresearch/sam3#installation)
- 官方影片介面為 `build_sam3_video_predictor()`，或同一程式庫的 `build_sam3_predictor(version="sam3")`；`start_session` 接受 MP4 或 JPEG 資料夾，`add_prompt` 接受文字、box 或點，`propagate_in_video` 輸出逐影格遮罩與 SAM 局部 object ID。[來源](https://github.com/facebookresearch/sam3#basic-usage)
- SAM 3 是共享視覺編碼器的 detector 與 tracker。初次無文字 box 在影片程式中視為**visual exemplar**，可能找到多個同概念物件；點提示帶 `obj_id` 則走單物件 tracker 路徑。SAM 內部 ID 不是 FindMind `phone_01`。[來源程式：影片推論](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_video_inference.py)、[請求介面](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_base_predictor.py)
- Tracker 延續 SAM 2 式 transformer encoder/decoder 與影片記憶。SAM 3.1 的 Object Multiplex 把物件分桶共用記憶，官方說明原 SAM 3 各物件個別處理；SAM 3.1 多物件加速不等同單目標任務收益。[來源](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)
- 所選 SAM 3 的非 multiplex 建構路徑預設 `use_fa3=False`；某些 RoPE attention 程式分支使用 PyTorch `sdpa_kernel(FLASH_ATTENTION)`，其他 attention 使用一般 `scaled_dot_product_attention`。因此不能憑已安裝 FlashAttention 套件或程式碼分支推定實際核心。[來源程式：builder](https://github.com/facebookresearch/sam3/blob/main/sam3/model_builder.py)、[attention](https://github.com/facebookresearch/sam3/blob/main/sam3/model/decoder.py)
- Mask prompt 由同一模型的 `add_mask` / instance-interactivity 路徑支援；本次主臂不用人工遮罩，避免引入額外標註。文字 `smartphone` 也不作為主臂，因其屬概念搜尋而非已知實體追蹤。

## 本機實測與 PROJECT_DESIGN_INTERPRETATION

- 官方程式碼固定於 `2345a4ad109ac29c569da749c91d84f10dc08c40`，SAM 3 權重 `facebook/sam3` revision `3c879f39826c281e95690f02c7821c4de09afae7`，`sam3.pt` SHA-256 `9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e`。本次選 `build_sam3_predictor(version="sam3")`；程式拒絕 SAM 3.1 權重名稱或 Multiplex model。
- 系統為 Windows 11、Python 3.12.8、PyTorch 2.10.0+cu128、RTX 5070 Ti 16 GiB。安裝 `triton-windows` 供官方模組載入，未在獨立 `.venv_sam3` 安裝 FlashAttention 3。詳細版本見 `environment_manifest.json`。
- test8 f804–f846 真正執行 box prompt 後，PyTorch profiler 觀察 `aten::_scaled_dot_product_efficient_attention`，故本次實際 attention 記為 **PYTORCH_MEM_EFFICIENT_SDPA**。未觀察到 FlashAttention 3，也不能把先前 SAM 3.1 的 Windows 故障直接推給 SAM 3。
- 同一凍結 f804 YOLO box 的單次 SAM 3 box prompt 產出三個 object ID。V2.6.2 的預測前選取規則為：只用提示影格 SAM 輸出框與凍結 YOLO box 的 IoU 決定一個 SAM-local ID，之後固定該 ID。若無交集即視為無目標。這是可重現的工程綁定規則，**不是**人工真值標註或 SAM 3 原生持久身分能力。
- 作為補充，凍結 YOLO box 中心可轉為單一正點，走官方 point/object-ID tracker 路徑。它與 box visual exemplar 的語意不同，單獨呈現，不混入主臂 A/B。
- 單一 box 對多個 instance 的輸出代表原始主臂不是直接一對一對照 SAM 2.1。所有品質指標必須以選定 ID 對應實體手機檢查；非空遮罩本身不能算成功。V2.6 Identity Guard 對兩臂完全相同，test7 f636 PROVISIONAL_MATCH 不可新初始化，test8 f804 CONFIRMED_MATCH 可新初始化。
