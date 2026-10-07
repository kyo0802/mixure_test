"""QC-gated fresh DEV Pilot 1 runner. Run only after human Evidence QC."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from memory_graph.pass_i.common import OUT, read, write, sha
from memory_graph.pass_i.pilot import parse_response, PROMPT_FILE
from memory_graph.pass_i.pilot1 import prepare_pilot1, PILOT1_MANIFEST


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if not args.prepare_only and not args.run:
        parser.error('Specify --prepare-only or --run')
    manifest = prepare_pilot1()
    expected = read(OUT / 'manifests/dev_pilot_1_hashes.json')
    if sha(PILOT1_MANIFEST) != expected['manifest_sha256'] or sha(PROMPT_FILE) != expected['prompt_sha256']:
        raise ValueError('Pilot 1 manifest or unchanged Pilot 0 prompt drifted; STOP')
    print(f"Pilot 1: {len(manifest['items'])} DEV pairs; {manifest['blind_first_count']} blind-first; prompt {expected['prompt_sha256']}")
    if args.prepare_only:
        return
    from memory_graph.pass_i.codex_transport import CodexTransport
    output = OUT / 'prelabels/dev_pilot_1'
    output.mkdir(parents=True, exist_ok=True)
    client = CodexTransport(output_dir=output)
    attempted = 0
    try:
        for entry in manifest['items']:
            if args.limit is not None and attempted >= args.limit:
                break
            item = read(ROOT / entry['evidence_package']['path'])
            if entry['split'] != 'dev' or item['item_id'] != entry['item_id']:
                raise ValueError('Pilot 1 DEV boundary violation')
            rawpath = output / f"{item['item_id']}.raw.json"
            if rawpath.exists():
                continue
            raw, text, runtime = client.infer(item)
            with rawpath.open('x', encoding='utf-8') as f:
                json.dump({'item_id': item['item_id'], 'raw_response': raw, 'raw_text': text,
                           'runtime': runtime}, f, ensure_ascii=False, indent=2)
                f.flush(); os.fsync(f.fileno())
            result = parse_response(text, item)
            value = {**result, 'valid': result['schema_valid'],
                     'raw_response_path': str(rawpath.relative_to(ROOT)),
                     'raw_response_sha256': sha(rawpath), 'raw_text': text,
                     'validation_error': result['error']}
            write(output / f"{item['item_id']}.json", value)
            attempted += 1
            print(item['item_id'], result['status'], result.get('parsed', {}).get('label') if result.get('parsed') else None,
                  flush=True)
    finally:
        client.close()


if __name__ == '__main__':
    main()
