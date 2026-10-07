import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_i.pilot import prepare, verify_pilot, public_item, record_response, PILOT_OUT
from memory_graph.pass_i.common import write, read_lines

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.prepare_only:
        m = prepare()
        print(json.dumps({'pairs': len(m['items']), 'blind_first': m['blind_first_count'], 'frozen': 0}))
        sys.exit(0)
    if not args.run:
        parser.error('Use --prepare-only or explicitly --run')
    manifest = verify_pilot()
    from memory_graph.pass_i.codex_transport import CodexTransport
    client = CodexTransport()
    start = time.perf_counter()
    attempted = 0
    try:
        for entry in manifest['items']:
            if (PILOT_OUT / f"{entry['item_id']}.raw.json").exists():
                continue
            if args.limit is not None and attempted >= args.limit:
                break
            item = public_item(entry)
            print('Request', item['item_id'], flush=True)
            raw, text, runtime = client.infer(item)
            result = record_response(item, raw, text, runtime)
            attempted += 1
            print('Completed', item['item_id'], result['status'], result.get('parsed', {}).get('label') if result.get('parsed') else None, flush=True)
            write(PILOT_OUT / 'dev_pilot_runtime.json', {'model': 'gpt-6.1-sol', 'model_revision': None,
                'transport': 'codex_app_server', 'latest_run_wall_seconds': time.perf_counter()-start,
                'requests_completed': len(list(PILOT_OUT.glob('PI_*.raw.json'))), 'frozen_items_sent': 0})
    finally:
        client.close()
