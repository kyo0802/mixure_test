# 兩位人工 GT 對齊摘要

原始紀錄：[19, 34]；物理事件標記：[19, 28]；非事件觀察：[0, 6]。

共 34 個待裁決群組，其中 19 組雙人對應候選；分類 {'ONE_REVIEWER_ONLY': 12, 'UNCERTAIN_EVIDENCE': 16, 'EVENT_TYPE_DISAGREEMENT': 2, 'NON_EVENT_CONFLICT': 4}。附加旗標 {'ONE_REVIEWER_ONLY': 15, 'IDENTITY_DISAGREEMENT': 26, 'UNCERTAIN_EVIDENCE': 27, 'TIMING_DISAGREEMENT': 14, 'EVENT_TYPE_DISAGREEMENT': 2, 'NON_EVENT_CONFLICT': 4}。

分類不是裁決：UNKNOWN 身分列為 IDENTITY_DISAGREEMENT，意指尚未解決，不代表已證實不同實物；不同 local ID 名稱本身不算衝突。

兩人九片 event_list_exhaustiveness 全為 NOT_ATTESTED。完整觀看不能產生負例資格；原始聲明保持原值。coverage 表依已知遮擋邊界切開，只是待人工核准的區間，未報遮擋也不等於已證明可觀察。

對齊只用人工標註。相同類別、型別及重疊時間只構成候選；related_groups 請檢查是否其實不同實物或不同事件。每個群組最多各一位審閱者的紀錄，不做傳遞式合併。

所有 owner_decision 均空白，尚無 authoritative GT。請見 EDITING_GUIDE.md。

Cross-group NON_EVENT_CONFLICT / EVENT_TYPE_DISAGREEMENT 只是重疊時間的不同解釋候選；不表示已證實互斥，也不合併可能連續發生的不同事件。
