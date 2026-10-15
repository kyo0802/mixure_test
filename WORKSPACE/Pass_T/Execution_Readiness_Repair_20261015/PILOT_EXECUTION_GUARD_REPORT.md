# Pilot Execution Guard Report

## Three distinct states

1. `draft_protocol` / CLI `dry-run`：metadata only、status=DRAFT、21決策PENDING、approval=None、execution=None、媒體PENDING。新的canonical draft SHA：`c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02`。
2. 人類核准後才可呼叫新的freeze writer。要求逐字freeze confirmation、非空reviewer、21個正確decision digests及各APPROVED、execution_authorized=false；核對完整draft/component後寫獨立freeze bundle/receipt。**本次未呼叫writer、未建立freeze。**
3. 實際run另要求綁frozen protocol SHA的execution confirmation、reviewer、32hex nonce、UTC expiry、18call IDs/budget，並保留原 `PASS_T_LOCAL_RUNTIME_APPROVAL` 與 `PASS_T_PHASE2B_REAL_RUN_PERMISSION` 外部環境gate。沒有任何自動設環境permission的程式。

MOCK reviewer records只用於CPU in-memory contracts；production freeze writer、真正model factory與real Bridge preprocessor拒絕MOCK。測試沒有把假資料提升成真正freeze/執行授權。

## A / Native integration

原Bridge預設synthetic path及V1C/V1D pin條款保留。只有明確 `real_pilot_mode=FROZEN_V1D_PILOT_V1` 且synthetic_only=false才走新的guard；guard於torch/processor imports之前檢查frozen/auth/runtime/bridge/schema/prompt/system/representation/source aliases/native PTS與model-visible限制。未認得mode、缺資料或hash不同直接拒絕，沒有globally移除synthetic guard。

FRAME_MATCHED_ONLY、8source/4units、dtype/order/PTS/RGB/patch/cap原有檢查保留；不宣稱8獨立temporal positions或attention。模型端引用語法不變；C3 temporal-unit disclosure只在receipt/report。

## B / Explicit execution route

`scripts/run_pass_t_v1d_pilot.py` 的預設是CPU dry-run，freeze/run均需各自明確參數與授權。新in-process route直接調原shared NF4，沒有HTTP/AVI/legacy prompt_path fallback；舊interfaces保留以供復現。原 `nf4.py`、`runtime.py`、`qwen_contract.py`、legacy transport/protocol/config/inference未改。

新CLI沿用已成功V1D worker的src、`artifacts/pass_i/runtime/vendor`、`outputs/current_development/video_event_experiment/.deps`三個既有搜尋路徑。本機venv不直接提供jsonschema，因此這個顯式整合是必要修補；沒有安裝/下載/換環境。獨立CLI import檢查可載入execution介面，model imports=[]。

新ObservedNF4 subclass只觀測原CPU preprocessing回傳的tensors、canonical hashes、完整input_ids、rendered text/system。它不修改原inputs、不替換generation controls、不修改shared generate。native既有tensor records還會比對相等。模型權重驗證/既有10GiB GPU/8GiB RAM loader gate及2GiB generation gate仍由原NF4執行。

supervisor在授權後才spawn worker／query資源：load120s、generation300s、request330s、proposed whole6060s；globalGPU>14.5GiB/ownedRSS>20GiB/systemRAM<2GiB停止。1s nominal polling保留觀察限制。獨佔authorization-use目錄與每call started claim防止同一permission/call重播；不重試、不加warmup。strict-invalid在健康時繼續；安全/程序/deadline問題停止並保存可用raw與缺結果狀態。

## Model-visible / media provenance

延用未改的既有payload schema/key/serialized-leak guard。Native in-process array的**validation-only projection**將已核准source descriptors映射到既有image schema，以執行同一key/leak檢查；projection不送模型。原actual Native payload仍media=[]，array由Bridge獨立驗形狀/順序/RGB。這不是放寬schema或隱藏新媒體；original payload/task/system hash另記。

執行時在任何媒體讀取前驗授權，逐PNG與已核准hash比對，確認index/nativePTS在hash-pin的authorized half-open boundary內，Uniform8固定；storyboard沿用已存在、已記錄hash的canvas，不生成新visual fixture。raw source video本體hash本次未驗；未來input PNG驗證與nativePTS provenance以已核准source metadata為依據，不能冒稱重新decode原影片取PTS。

每call receipt綁frozen protocol/auth、component hashes、source metadata/full-frame-list SHA、frame alias/native PTS、actual media hashes、payload/generation/rendered/tensor hashes和temporal limitations。

## Remaining execution-only checks

Current real PNG/storyboard identity、actual pixel decode/array/processor grids、weights/currentGPU capacity、CUDA數值/timeout enforcement及真實18call均為 **PENDING_AUTHORIZED_EXECUTION**。CPU tests只驗guard與mock orchestration，未聲稱這些已通過。所記錄核准JSON是信任的人類來源記錄，不是cryptographic human-authorship簽章。
