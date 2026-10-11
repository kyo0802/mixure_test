"""Local Stage B commands; no inference or annotation shortcuts."""
import argparse
import json
from .policy import OUT, verify_gate, preservation, exclusive, utc
from .projection import prepare
from .storage import inventory, progress
from .finalize import finalize


def _main():
    parser = argparse.ArgumentParser(description='Pass T Phase2a V2 human Event GT tools')
    parser.add_argument('command', choices=['prepare', 'validate', 'progress', 'finalize', 'preservation', 'gui'])
    parser.add_argument('--round', type=int, choices=[1, 2], default=1)
    parser.add_argument('--strides', type=int, nargs='+', help='Explicit human-supplied positive frame strides; no default')
    args = parser.parse_args()
    verify_gate()
    if args.command == 'prepare':
        result = prepare()
    elif args.command == 'validate':
        manifest, rows = inventory()
        check = preservation()
        result = {'checked_at_utc': utc(), 'response_count': len(rows),
                  'valid': sum(r['valid'] for r in rows), 'invalid': sum(not r['valid'] for r in rows),
                  'results': rows, 'preservation': check,
                  'status': 'NO_GENUINE_EVENT_GT_YET' if not rows else 'VALIDATED' if all(r['valid'] for r in rows) and not check['errors'] else 'INVALID'}
        from uuid import uuid4
        exclusive(OUT / 'validation_runs' / (str(uuid4()) + '.json'), result)
    elif args.command == 'progress':
        result = progress()
    elif args.command == 'finalize':
        result = finalize(strides=args.strides or ())
    elif args.command == 'preservation':
        result = preservation()
    else:
        from .viewer import launch
        launch(round_=args.round)
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get('invalid', 0) or result.get('errors') or result.get('preservation', {}).get('errors'):
        raise SystemExit(1)


def main():
    try:
        _main()
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error), 'error_type': type(error).__name__}, ensure_ascii=False, indent=2))
        raise SystemExit(2) from None


if __name__ == '__main__':
    main()
