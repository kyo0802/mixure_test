# FindMind 離線人工 GT 標註工具

給受邀審閱者：這份工具用來獨立觀看 test1–test9 原片，記錄你實際看到的物件事件、狀態與審閱範圍。請只依畫面判斷，不先看其他人的答案或模型結果。

## 下載

**[下載完整標註工具 ZIP（含九支影片）](https://github.com/kyo0802/mixure_test/archive/refs/heads/codex/offline-gt-annotator.zip)**

或開啟[獨立標註分支](https://github.com/kyo0802/mixure_test/tree/codex/offline-gt-annotator)，按 **Code → Download ZIP**。請確認分支是 `codex/offline-gt-annotator`。這個分支只提供審閱工具與原片。

若 GitHub 顯示 404，請先登入有儲存庫存取權的帳號，並請專案負責人確認權限；也可直接向負責人索取 `findmind-gt-annotator.zip`。不需要 Git、GitHub Desktop 或下載整個研究專案。

## 開始（不需安裝）

1. 下載上方 ZIP 或負責人提供的 `findmind-gt-annotator.zip`，並**完整解壓**。不要直接在 ZIP 預覽內開網頁。
2. 確認 `index.html`、四個 JavaScript、CSS 與 `videos/` 都在同一個資料夾內。
3. 用 Chrome 或 Edge 雙擊開啟 `index.html`。網址為 `file:///.../index.html`；不需連網、登入或啟動伺服器。
4. 輸入審閱者 ID／暱稱，選擇分工影片，建立獨立 session。每位審閱者各自建立，不共用別人的檔案。
5. 左側切換影片，中間播放完整原片，右側新增事件、state 與人工覆蓋。

GitHub ZIP 解壓後，打開最外層資料夾即可找到 `index.html`。負責人提供的獨立 ZIP 中，入口在 `findmind-gt-annotator/index.html`。若已取得完整研究專案，入口則在 `tools/findmind-gt-annotator/index.html`。不需任何模型、Python、Node.js 或專案環境。

請下載到電腦後開啟；GitHub 上的 HTML 原始碼頁不是可操作的標註網頁。

## 操作與保存

- 先讀 [標註準則](ANNOTATION_GUIDE.md)。只依畫面與原片判斷，不參考任何模型答案。
- 事件：暫停 → 設開始／結束時間 → 填物件與片內 ID → 填前後 state、可見度、證據秒數與把握 → 儲存。已儲存項目可跳轉、編輯、刪除。
- State：只標重要時間點；物理狀態與可見度分開填。
- 覆蓋：手動記錄已審閱／不確定區間，最後再確認全片狀態。播放進度不會自動填寫覆蓋。
- 本機暫存只是方便續做。**每次離開前按「下載備份」並確認下載成功。** 換瀏覽器或搬資料夾後，使用「匯入先前 JSON」。
- 完成分工後按 **「匯出標註成果（JSON）」**，將 `findmind_gt_<暱稱>_<session>.json` 傳給專案負責人。部分完成也可匯出；FINAL 不會把它變成完整負例。
- 匯入會先驗證版本、影片 hash、時間範圍與 ID，再要求確認載入；錯誤檔不覆蓋目前工作。

## 交件前確認

1. 使用你自己的 reviewer ID 與 session；先確認負責人指派的影片，不確定分工時先聯絡負責人。
2. 記錄確定看到的拿起／放下；只有接觸、遮擋或證據不足時保留不確定，不能猜成事件或無事件。詳細規則見 [標註準則](ANNOTATION_GUIDE.md)，或直接在工具點選操作指南。
3. 完成每支分工影片後，手動填已審閱與不確定區間。沒有看完就如實標為部分完成。
4. 匯出 JSON，確認電腦實際出現下載檔。將這個 JSON 傳回交付工具給你的專案負責人；不必傳影片、不需 push GitHub。工具本身不會上傳資料。
5. 若需更正，匯入原 JSON 後修改再匯出，告知負責人這是修訂版並保留原檔。不要修改 JSON 內的來源 hash 或人工合併別人的內容。

正式標註前可用獨立 `MANUAL_TEST_ONLY` session 熟悉操作；測試 JSON 不要當正式成果提交。完成標註後，主持人會另做來源檢查與爭議裁決，不會以多數決自動產生 GT。

## 影片與時間

內附 test1–test9 **完整原始 H.264 MP4**，無剪輯、無轉碼、無變速；SHA-256 與原片一致。可按「選取本機 MP4 並驗證 SHA-256」檢查收到的檔案。

所有標註使用原片秒數。逐影格按鈕實際是 seek 到原生 PTS 時間點；HTML5 解碼可能落在鄰近影格，**不可宣稱 frame-accurate**。匯出 `source_frame_index=null`，鄰近索引只作導航提示。

影片不能播放時，先確認已完整解壓、`videos/` 有九個實際 MP4（不是 Git LFS pointer），再以支援 H.264 的 Chrome／Edge 開啟。可用內建檔案選擇器重新選正確 MP4。沒有伺服器備援，也不需要安裝依賴。

## 驗收狀態

此開發環境的內建瀏覽器安全政策禁止 `file://`，因此不能宣稱已實測 Chromium 雙擊操作。發送他人前，請依 [本機人工驗收](MANUAL_ACCEPTANCE.md) 在 Chrome／Edge 完成一次。影片解碼與資料契約／收件測試的實際結果由負責人報告提供。

2026-10-18：專案負責人已回報「已完成播放、標註與匯出再匯入」。這是使用者實機回報；尚未提供瀏覽器版本或完整逐項紀錄，不預填其他驗收核取方塊。
