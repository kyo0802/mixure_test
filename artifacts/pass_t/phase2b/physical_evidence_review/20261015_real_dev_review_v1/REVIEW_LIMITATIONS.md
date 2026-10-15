# Review limitations

- 只顯示既有八張 sampled source frames；沒有完整影片、額外 seek 或新取樣。影格間隙可遮蔽轉換，沒有 prior observation 不能補推 BEFORE。
- 影格 hash/alias/PTS 對上不證明物理事件正確；來源 PTS 是既有 metadata，本次未重新從原始影片驗證時鐘或 movie SHA。
- 一張 held-state 影像不能確立 pickup 時間與位置；不同狀態之間的 bracket 不是直接觀察的 event duration。
- Native FRAME_MATCHED_ONLY：8 source frames / 4 temporal units，不能推稱八個獨立被注意的時間位置；processor resize/grid metadata 也不是 attention 的視覺重現。
- Storyboard 為一張既有帶標籤拼圖；multi-image 為分別供應，native 為 video array。原始 source sequence 相同不等於模型視覺感知相同。
- test5/test7 是 non-exhaustive known PICKUP windows；既有 GT 只是 scoped reference，不能把 unmatched prediction 當 FP，或把 Call 2 當經人工確認的 FN。無 validated PLACEMENT positive。
- 模型 card/phone/ball/object 名詞不可當作 target identity；畫面狀態差異不可自動推定特定因果。
- OUTPUT_CONTRACT_FAILURE 與 PHYSICAL_EVIDENCE_ASSESSMENT 分開：五筆 event-bearing outputs 都是 strict-invalid，沒有修復，不進 authoritative matching。
- 全部五筆 human disposition 都為 UNREVIEWED；套件製作完成不等於 physical PICKUP 正確性已驗證。沒有新 GT、exhaustive list 或正式統計指標。
- HTML 不需網路或外部 JavaScript。原始資產以 repo 相對路徑連結：需保留 repository 結構，單獨移走此目錄會失去原始圖連結。下載 human JSON 是唯一保存方式；不自動寫入 annotations/GT。
