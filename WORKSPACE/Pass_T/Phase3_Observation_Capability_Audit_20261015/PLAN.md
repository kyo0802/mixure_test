# Phase 3A Observation Capability Audit Plan

**Goal:** 以現有 source、tests、real stored artifacts、human annotations 分開證據層級，判定未來 PICKUP／PLACEMENT validator 可取得什麼觀察。

**Method:** 單一工作樹，僅 CPU read-only 文字／JSON／SQLite inspection；不 import 會載入模型的專案模組、不跑 inference／pipeline／video decode。不修改既有 source、GT、graph、歷史報告。只新增本資料夾報告及固定 WORKSPACE 導航。

- [x] 保存 source／tracked-diff baseline，定位目前 entrypoint 與多代 runner，分開 current identity、legacy graph、Pass T experimental paths。
- [x] 逐層檢查 detection、tracking、SAM、Re-ID／guard、event builder、time mapping、spatial／graph producer-consumer 與 tests。
- [x] 擷取代表性 real artifacts，統計實際 record counts、fields/nulls、identity／PTS／confidence；不把 mocks/schema 當 real evidence。
- [x] 在 first-party source、tests、configs 範圍搜尋 hand／pose／contact／state／camera compensation，記錄 negative-search scope。
- [x] 產生九份指定 audit files（含48欄 observation matrix、真實 dataflow、三層概念草稿與3A–3F roadmap）。
- [x] 核對引用、保留 source/status、更新最新報告入口並停止。沒有 Phase3 implementation、prototype、schema freeze、commit 或 push。
