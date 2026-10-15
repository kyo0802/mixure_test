# Matcher Semantics Review

## Discrepancy before repair

舊 `evaluation._compatible` 在GT有寬度時先計overlap length。若預測是GT區間內的point，overlap長度=0，舊碼改算到endpoint的距離，可能大於0並拒絕tolerance0。這是程式邊界問題；沒有讀真實GT判定六窗是否觸發。

## Versioned candidate implementation

- 新policy：`CLOSED_INTERVAL_GAP_V1`。點t與GT[a,b]：`max(a-t,0,t-b)`；GT[a,b]與prediction[c,d]：`max(c-b,a-d,0)`。
- 使用 `Decimal(str(timestamp))` 做固定十進位容差比較，沒有私自epsilon。既有native PTS數值原樣使用，不重建或校準GT。
- Point在區間內／端點、interval相交／接觸均gap0；disjoint為最近間隙。missing、nonfinite、反向interval不match；unknown時間與uncertain target association不match；沒有event citations也不match。
- 同type、greedy按(distance,GT index,pred index)排序，GT/pred各用一次。不是optimal maximum-cardinality。
- `match_known_events` 預設仍 `LEGACY_OVERLAP_V0`，歷史 `_compatible` 本體未變。只有顯式新policy才改用新公式；新pilot draft另pin此policy，且須人類核准。未知policy拒絕，不默認fallback。
- 新policy要求 `bounded_interval_overlap_required=False`。0、0.2、0.5秒在新gated evaluation均輸出，不選事後最好的tolerance。
- BEFORE/AFTER evidence brackets是時間相容區間，不是物理動作duration；不創midpoint、不推持續狀態。nonexhaustive已知PICKUP仍只match已支持子集，額外pred為UNEVALUATED；uncertain window不當negative。

CPU tests包含上述幾何/邊界、0.1→0.3的0.2秒邊界、略超界不match、duplicate一對一、missing/unknown/insufficient association與legacy復現。這些是software mock timing，不是physical-event GT。

Source差異：[EXACT_SOURCE_DIFF.patch](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/EXACT_SOURCE_DIFF.patch)；最終測試共53/53通過。
