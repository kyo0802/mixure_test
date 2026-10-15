# 歷史 smoke／tokenizer 稽核補充與最終交付

| Version / attempt | Tokens | Generation receipt seconds | Strict JSON | EOS |
|---|---:|---:|---|---|
| V1 / single_image | 253 | 80.164 | FAIL | NOT_VERIFIED |
| V1 / multi_image | 362 | 80.083 | FAIL | NOT_VERIFIED |
| V1 / storyboard | 613 | 80.159 | FAIL | NOT_VERIFIED |
| V1 / synthetic_video | 404 | 9.282 | FAIL | NOT_VERIFIED |
| V1 / structured_contract | 183 | 4.525 | FAIL | NOT_VERIFIED |
| V2 / structured_contract_v2 | 179 | 49.342 | PASS | NOT_VERIFIED |

V1 五筆全部因 code fence 被 strict parser 拒絕；前三筆約80秒且文字未完成，與當時 generation deadline 相容。這是保留的失敗，沒有剝fence或改寫raw output。後兩筆完整文字仍格式失敗。V2179tokens在512cap以下、49.34秒，schema/citations通過；未記錄EOS token，不能把完整JSON推論成EOS。Loader20.44秒與generation時間分開；processor/prefill未獨立記錄，新long-shape資源仍RUNTIME_NOT_VERIFIED。

Tokenizer與generation/config欄位、來源與hash見historical_failure_tokenizer_audit.json。Tokenizer最大length是設定宣告，不是實測NF4/GPU可承受context。V1/V2差異不是單純prompt效應：system formatting、tokencap、deadline同時不同，不能據此建立controlled causal superiority。沒有使用這些預測來挑選任何DEV影格。

最終distinct executed tests：42個新測試＋16個既有安全回歸＝58 passed，0最終failed/skipped；23個既有測試deselected。初次fixture漏source_frame_index與Windows路徑206錯誤保留在原JUnit，修正fixture/使用extended path後原assertions通過，未修改core。中間40項重跑與後續42項是重疊，不重複累加。

保護驗證：27,841個既有檔案hash一致，HEAD/index/tracked diff一致，15個checkpoint檔案符合歷史audit，最終重新hash不變。新metadata補充沒有修改sealed候選manifest或原offline receipt。本namespace的失敗candidate001/002留存，canonical成功候選是candidate003。

主要待解：video system/generation parity、video實際937664pixel/frame超過宣告200704、processed-frame citation alias限制、參考圖模型授權及test1缺reference、matched-shape容量、0.2s容差尚無獨立task依據與完整人工批准。None未被默認批准，512／180s亦未被宣稱足夠。

已實際執行且只離線的CLI：preflight.py build、video-check、timing-check、finalize；輸出存在時build拒絕覆寫。新的capacity probe執行CLI尚未實作，本次只有設計，沒有虛構或執行命令。下一步請閱讀22項protocol decision sheet並指定選項；若要做capacity probe或adapter修補需另授權該未來任務。解決後才交付完整protocol供批准／未來freeze；再獨立RUN_PHASE2B_EXPLORATORY_PILOT。

**PASS_T_PHASE2B_QWEN_NF4_PREFLIGHT_COMPLETE_AWAITING_USER_PROTOCOL_DECISIONS**

PROTOCOL_NOT_READY_TO_FREEZE。
