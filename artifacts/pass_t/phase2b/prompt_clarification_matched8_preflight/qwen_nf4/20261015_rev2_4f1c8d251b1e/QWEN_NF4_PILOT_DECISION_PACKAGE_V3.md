# Pilot decision package V3

**PROPOSED_AWAITING_USER_APPROVAL；PROTOCOL_NOT_READY_TO_FREEZE**。

Sampling policy UNIFORM_8和representation Multi/Storyboard/Video是不同軸，不列成同級條件。六cleanDEV：test1 W03/W05dedup、test2 W01、test5 W01 casealerts；test5W05/test7W05 non-exhaustive knownPICKUPmatching；額外predictions UNEVALUATED；test8uncertainty descriptive；test3excluded禁止cleanrun。formaleligible0、CAUSALITY_UNVERIFIED，無正式metrics/泛化/sessionindependence聲稱。

| Decision | Verified evidence | Proposed setting | Unresolved risk | User approval required |
|---|---|---|---|---|
| Prompt | V1C659tasktokens，原contract保留 | 批准核心A/B/C，仍不含identity條款 | 未測branchcoverage | YES |
| Target ambiguity | INSUFFICIENT_EVIDENCE CPU接受；無新schema | 單獨批准或拒絕pendingexactclause | technicalacceptance≠policyapproval | YES |
| Matched Video8 | 13/13 CPUarray source/order匹配 | 接受FRAME_MATCHED_ONLY或選12callB | pairedtime與8alias/4unit；原runtimebridge未實作 | YES |
| Reference NONE | 沒有referencepixels／extra tokens | 六clean DEV commonNONE | opaqueTARGET_A可能無unique association | YES |
| Pixels | 200704 effectivecap；actualgrids已記 | 固定原cap/3col480×270+32label | 2016/240/1008visualtokens不相等 | YES |
| Sampling | 六DEV既有uniform8indices全重現 | 原round ties-to-even/endpoints | 可能漏短事件；不調offset | YES |
| Output budget | 原633max、無capfailure；candidate尚未推論 | 1024/greedy/seed42 | realmulti-event容量未知 | YES |
| Timeout | load120/gen300/request330 proposal | 固定界線且preservepartial | 18×330=99min未含load/prep/retry | YES |
| Matching time | 原V2status+nativePTS權威保存 | 0/.2/.5全報；point/closedinterval/uncertainUNDEFINED、一對一 | 現greedy/evaluatorstatus須獨立review；不拿wholeevidenceenvelope當duration | YES |
| Run order | prospective18与12orderhash已列 | 批准選定variantorder及optionalrepeat | 未按答案排序；最後runtimehash尚缺 | YES |
| Holdout | 六evaluation+onewarmup先鎖再prompt | 沿已鎖manifest，不改fixture | 作者知概念；2.5Drender與realworld差異 | YES |
| Regression | 18/12variants+coveragegate已寫 | 另授權明確variant/extra warmup/4repeat數 | 尚未批准、未執行、無效能證据 | YES |
| Real cohort | 2knownpickup/3negative/1uncertain，test3排除 | limitedexploratory；formal0 | causality/sessionindependence未建立 | YES |
| Actual freeze | 沒有任何newfreeze | 後續finalsettings/componenthash定稿再人審 | 21項仍有UNRESOLVED | YES_SEPARATE_GATE |

## 21個freeze gate

| Requirement | Status |
|---|---|
| 1 collect-all replay | RESOLVED |
| 2 Validator hash unchanged | RESOLVED |
| 3 known-state taxonomy | RESOLVED |
| 4 prompt candidate approved | UNRESOLVED |
| 5 identity clause approved/rejected | UNRESOLVED |
| 6 fixtures locked before prompt | RESOLVED |
| 7 regression design approved | UNRESOLVED |
| 8 regression executed/reviewed | UNRESOLVED |
| 9 CPU preflight performed DEV/synthetic | RESOLVED |
| 10 native/model-time mapping for approved use | UNRESOLVED |
| 11 runtime model-consumed alias policy/granularity | UNRESOLVED |
| 12 approved representation budgets | UNRESOLVED |
| 13 point/interval/uncertain matching approved | UNRESOLVED |
| 14 timing sensitivity approved | UNRESOLVED |
| 15 approved final model-visible prompt hashes | UNRESOLVED |
| 16 generation settings approved | UNRESOLVED |
| 17 failure/retry approved | UNRESOLVED |
| 18 proposed run order fixed | RESOLVED |
| 19 source cohort fixed | RESOLVED |
| 20 frame/fixture/sourceasset hashes verified | RESOLVED |
| 21 explicit final protocol human approval | UNRESOLVED |

CPU數值mapping已建立並保存，不代表Video已符合批准的精度與aliaspolicy。原V3runtime固定encodedvideo sampling路徑，publicnativearray預檢沒有偷偷修改backend；futurebridge是否可整合須獨立審查與授權。0.1s偏差界線仍只是本任務要求測試的proposal。

GT匹配提案沿前audit：exactsource PTS以tick/timebase或Decimal表示，不加浮點epsilon當真值；bounded使用人工存的event_time而不是整段before/after證據包，closedinterval最短距離；uncertainGT/pred timingunknown→time compatibilityUNDEFINED，type另描述；最大一對一matching/tie規則需獨立CPUgate。沒有在本任務修改evaluator、計分或定tolerance。0/.2/.5全部報而非挑最佳。

精確下一步：請人審核心prompt、pendingidentityclause、Video FRAME_MATCHED_ONLY與12callvariant選擇、budget/retry/coverage等表。若選A，還須批准原生array與runtime橋接的獨立工程任務，不能直接執行本CPU腳本充作VLMregression；若選B，可另授權固定12callsyntheticregression及明確optionalwarmup/repeat數。未收到明確新授權前，不跑任一variant。

之後freeze和RUN_PHASE2B_EXPLORATORY_PILOT仍是兩道獨立人類gate。此次準備任務不授權任一推論。
