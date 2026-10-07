"""Verify actual sent requests/completions and preserved source artifacts."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_i.common import OUT, read, read_lines, write, sha
from memory_graph.pass_i.pilot import verify_pilot, public_item, PROMPT_FILE, PROMPT_SOURCE, PILOT_OUT, parse_response, priority, MODEL
from memory_graph.pass_i.codex_transport import turn_input
from memory_graph.pass_i.builder import protected_snapshot


def main():
    manifest = verify_pilot()
    entries = {p['item_id']: p for p in manifest['items']}
    rows = read_lines(PILOT_OUT / 'dev_pilot_prelabels.jsonl')
    raw = read_lines(PILOT_OUT / 'dev_pilot_raw_responses.jsonl')
    prompt = PROMPT_FILE.read_text(encoding='utf-8')
    errors, count = [], 0
    def check(value, message):
        nonlocal count
        count += 1
        if not value:
            errors.append(message)
    original = PROMPT_SOURCE.read_bytes().split(b'## BEGIN PASS I VISUAL ANNOTATOR SYSTEM PROMPT', 1)[1].split(b'## END PASS I VISUAL ANNOTATOR SYSTEM PROMPT', 1)[0].strip(b'\r\n')
    check(PROMPT_FILE.read_bytes() == original, 'Saved prompt bytes differ from supplied prompt')
    requested = list((PILOT_OUT / 'requests').glob('PI_*.json'))
    for path in requested:
        check(path.stem in entries, 'Non-pilot request sent')
        if path.stem not in entries:
            continue
        entry = entries[path.stem]
        item = public_item(entry)
        request = read(path)
        check(request['thread_start']['baseInstructions'] == prompt, 'Prompt changed')
        check(request['thread_start']['model'] == MODEL, 'Wrong requested model')
        check(request['thread_start']['ephemeral'] is True, 'Conversation history enabled')
        check(request['turn_input'] == turn_input(item, prompt), 'Actual sent image/text differs from whitelist')
        check(entry['split'] == 'dev', 'Frozen request')
    raw_by_id = {r['item_id']: r for r in raw}
    token_usage = {'inputTokens': 0, 'outputTokens': 0, 'reasoningOutputTokens': 0, 'totalTokens': 0}
    tool_types = {'commandExecution', 'fileChange', 'mcpToolCall', 'webSearch', 'dynamicToolCall', 'imageGeneration', 'collabAgentToolCall'}
    for r in raw:
        check(r['item_id'] in entries, 'Non-DEV response')
        check(r['raw_response']['thread_start_result']['model'] == MODEL, 'Actual model substitution')
        events = r['raw_response']['events']
        check(not any(e.get('method') == 'item/started' and e.get('params', {}).get('item', {}).get('type') in tool_types for e in events), 'Model used a tool')
        usage = [e['params']['tokenUsage']['total'] for e in events if e.get('method') == 'thread/tokenUsage/updated']
        if usage:
            for k in token_usage:
                token_usage[k] += usage[-1].get(k, 0)
    for r in rows:
        item = public_item(entries[r['item_id']])
        parsed = parse_response(raw_by_id[r['item_id']]['raw_text'], item)
        check(parsed == r, 'Parsed output silently changed')
        saved = read(PILOT_OUT / f"{r['item_id']}.json")
        check(sha(ROOT / saved['raw_response_path']) == saved['raw_response_sha256'], 'Raw response changed')
        if r['schema_valid']:
            check(r['needs_human_review'] == priority(r['parsed']), 'Wrong deterministic review priority')
    check(len(raw_by_id) == len(raw), 'Duplicate raw responses')
    check(len({r['item_id'] for r in rows}) == len(rows), 'Duplicate parsed responses')
    hashes = read(OUT / 'manifests/manifest_hashes.json')
    for path, h in hashes.items():
        check(sha(ROOT / path) == h, 'Original dataset manifest changed: ' + path)
    baseline = read(OUT / 'manifests/protected_before.json')
    check(protected_snapshot() == baseline, 'Protected V297/V2101 file changed')
    result = {'passed': count-len(errors), 'failed': len(errors), 'errors': errors,
        'requests_audited': len(requested), 'raw_responses_audited': len(raw),
        'frozen_requests': sum(p.stem not in entries for p in requested),
        'protected_files_verified': len(baseline), 'token_usage': token_usage,
        'complete': len(raw) == len(entries)}
    write(OUT / 'reports/dev_pilot_final_audit.json', result)
    print(json.dumps(result, indent=2))
    sys.exit(bool(errors))


if __name__ == '__main__':
    main()
