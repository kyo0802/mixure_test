"""Readable audit views; never invent a human adjudication or a visual conclusion."""
import json
from ..phase2a_v2 import policy


def markdown(result, completion=None):
    lines = ['# Pass T Phase 2a V2 External Annotation Import Report', '',
             '## 結果與使用範圍', '',
             '`' + (completion or 'AUDITED_ONLY') + '`', '',
             '本次驗證檔案完整性、原始契約與標註結構；尚未獨立視覺確認事件，也沒有確認 reviewer 的真實身分。',
             'DEV 機器資格與人工品質放行分開呈現。formal_eligible = 0；CAUSALITY_UNVERIFIED。', '',
             '## 實際統計', '', '| 項目 | 數值 |', '|---|---|']
    for key, value in result['summary'].items():
        lines.append(f'| {key} | {json.dumps(value, ensure_ascii=False)} |')
    lines += ['', '## 來源與完整性', '', f"ZIP SHA-256: `{result['archive_sha256']}`", '',
              '```json', json.dumps(result['authority'], ensure_ascii=False, indent=2), '```', '',
              '## 每視窗狀態', '',
              '| 視窗 / item | 原 reviewer | Outcome | 分類 | 原 V2 full-window | 品質放行 |', '|---|---|---|---|---|---|']
    for r in result['records']:
        source = r['source'] or {}
        window = ', '.join(source.get('original_pack_ids', []))
        lines.append(f"| {window}<br>{r['annotation_item_id']} | {r['reviewer_id']} | {r['response'].get('window_outcome')} | {r['category']} | {r['evaluation']['full_window_event_evaluation_supported']} | {r['quality_cleared_for_model_scoring']} |")
    lines += ['', '## 人工待辦與原始引用', '',
              '身分拼法由本人或專案負責人明確記錄確認；不得以拼字相似推定同一人或兩位独立評分者。',
              '以下引用均來自授權視窗。描述是標註者原文，並非本次審核的視覺判定。起終點、PTS 與雜湊由程式確認；物理事件是否可見由人判斷。', '']
    for r in result['records']:
        source = r['source'] or {}
        lines += [f"### {', '.join(source.get('original_pack_ids', []))} — {r['annotation_item_id']}", '',
                  f"原 reviewer：`{r['reviewer_id']}`；round `{r['review_round']}`；submission `{r['submission_id']}`。", '',
                  f"原始 response SHA-256：`{r['response_sha256']}`；ZIP 內路徑：`{r['original_member_path']}`。", '',
                  f"Schema / semantic / provenance / original receipt：`{r['schema_valid']} / {r['semantic_valid']} / {r['provenance_valid']} / {r['immutable_receipt_valid']}`。", '',
                  f"原始 outcome：`{r['response'].get('window_outcome')}`；exhaustiveness：`{r['response'].get('event_list_exhaustiveness', 'NOT_APPLICABLE')}`。", '',
                  '待辦旗標：' + ', '.join('`'+f+'`' for f in r['human_review_flags']), '',
                  '原 validator 排除理由：`' + json.dumps(r['production_validation']['exclusions'], ensure_ascii=False) + '`。', '',
                  '獨立驗證錯誤：`' + json.dumps(r['independent_validation']['errors'], ensure_ascii=False) + '`。', '']
        if r['category'] == 'QUARANTINED_EXCLUDED':
            lines += ['**僅保留稽核用途。** 請確認肯定揭露是否為本人原意；不得假設是誤勾，不得用模型答案或答案表協助事後修正。禁止 clean DEV 計分。', '']
        elif r['category'] == 'ACCEPTED_EXPLORATORY_POSITIVE':
            lines += ['**候選探索性正例。** 請檢查 BEFORE → TRANSITION → AFTER 的目標與物理轉換；消失、遮擋、手接近或 detector loss 本身不足以證明 PICKUP。待視覺與身分確認後才能作有限探索性比對；未列事件永遠不能在本版本視為負例。', '']
        elif r['category'] == 'ACCEPTED_STRICT_NEGATIVE':
            lines += ['**原 V2 規則支持 full-window DEV。** 嚴格無事件聲明已通過原 validator；reviewer 身分釐清前尚未品質放行。不可升格正式 benchmark。', '']
        elif r['category'] == 'ACCEPTED_UNCERTAIN':
            lines += ['**僅保留不確定案例分析。** 不得當作無事件負例，也不得填補未知物理狀態。', '']
        else: lines += ['請依上述驗證結果與待辦旗標處理；本報告不選擇優先答案，也不授予人工批准。', '']
        lines += ['| role | frame / native PTS | 標註者原文 | 授權圖檔 |', '|---|---|---|---|']
        for c in r['authorized_frame_checklist']:
            image_path = str(policy.ROOT / c['image_path']).replace('\\', '/')
            description = (c['annotation_description'] or '(未提供文字描述)').replace('|', '\\|').replace('\n', ' ')
            lines.append(f"| {c['role']} | {c['frame_id']} / {c['source_timestamp_s']} | {description} | [{c['frame_id']}](<{image_path}>) |")
        lines += ['', '逐影格 SHA-256、PTS、source item 與完整原始答案都保留在 JSON 報告與 immutable store。', '']
    lines += ['## Phase 2b 之前的確切人工動作', '',
              '1. 明確記錄 `annotator_Huang` 與 `annotater_Huang` 是否同一人；原字串與答案保持不變。',
              '2. 確認 test3 W07 七項肯定揭露是否為原意；目前維持排除，若需修正應另行授權可追溯的前瞻修正／裁決流程。',
              '3. 以授權影格檢查 test5 W05 PICKUP 是否確有支持的物理轉換，尤其 AFTER 消失描述。',
              '4. 同樣檢查 test7 W05；test3 的 PICKUP 也未獨立視覺確認，且揭露排除不因視覺確認而解除。',
              '5. 決定是否另建前瞻、完整可評估的正例標註與負控制抽樣，才設計 full-window 評估。現有 NOT_ATTESTED 不可事後自動改成 exhaustive。', '',
              '## 限制', '']
    lines += ['- ' + limit for limit in result['limits']]
    return '\n'.join(lines) + '\n'
