# CPU預檢保存報告

Before/after保護 29746 檔，changed=[]；Git HEAD/index/trackeddiff/stageddiff/status均不變。HEAD=149c70a21b51160e4316a9334758417d057aee80。原Validator、PredictionV1、V2格式、V3runtime/code、historicalcapacity raw/receipts、Phase2a policy/GT與sidecars均在保護範圍。6權重binary不讀、不copy、不load；原權重metadata沿既有manifest，沒有本次model能力宣稱。

GPU before={'returncode': 0, 'stdout': '0, NVIDIA GeForce RTX 5070 Ti, 1569 MiB, 14429 MiB, 0 %\n', 'stderr': ''}；GPU after={'returncode': 0, 'stdout': '0, NVIDIA GeForce RTX 5070 Ti, 1637 MiB, 14361 MiB, 1 %\n', 'stderr': ''}；computeprocessbefore/after在preservation.json，全部runningprocesslist在PREFLIGHT_BEFORE/AFTER。Nvidia WDDM/N/A與外部程序限制保留；記憶體變動可来自其他程序，不是單靠GPU數值證明否定。所有script環境={'CUDA_VISIBLE_DEVICES': '-1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}；CPUprocessor每次記cuda_initialized=false。

強制：network socket connect拒絕，weightbinary open拒絕，torch.load/jit.load/CUDA初始化拒絕，PreTrainedModel.from_pretrained和GenerationMixin.generate被fail-closed guard取代；只有本機AutoProcessor.from_pretrained local_files_only/trust_remote_code=false，沒有serverlaunch。全新script AST scan=10檔，forbiddencalls=[]；permitprocessor唯一loader記錄完整。Torch/PIL/processor CPU張量是影格處理，不是model forward。只存張量shape/hash，沒有大型tensor檔。

CPU tests={'errors': [], 'failures': [], 'new_model_calls': 0, 'passed': 60, 'skipped': [], 'tests': 60}。同60uniquechecks最後全pass；最初opaquefilename測試以POSIXslash解析Windows路徑而誤報，初始testlog及序列化失敗的空json保存在processor_diagnostics/cpu_tests_initial。修正test Path.name及error-to-string後重跑，不改fixtures/prompt/validator；不把兩次測試加成120unique。

CPUprocessor初版請求return_metadata=true又return_tensors=pt，VideoMetadata不能tensorize；另一次float32 seconds_per_grid被不合理1e-12精度assert阻擋。保留trialinputs/log，不改原runtime；正式CPU稿return_metadata=false，另存metadata觀察；時間採actualfloat32輸出，nominal對照仅做serialization精度check。這是CPU預檢instrumentation修正，不是model-output repair或自動generation retry。locked56sourceframes與generatorhash保持原樣。

Shadow對wrong-type list enums增加dependencytypeguard，原33影子/strict结果重確認不變，STEP_RECEIPT_0_CONFIRMATION記before/aftermodulehash；productionvalidator不改。Prompt第一次literalguard把ontology lifted當私有lift子字串，採wholeliteral檢查後才寫prompt，沒有生成第二個候選。

new_model_calls=0，GPUinference=0，Phase2apredictions=0，freeze=0，Graphwrites=0，commit/push=0。核對範圍只涵蓋本任務script與guard、所列29kfilehash、開始/結束processsnapshot，不是全機連續追蹤，不能证明別的程式沒有GPU活動。所有新writes限本namespace。工程fixturelock不是protocolfreeze。
