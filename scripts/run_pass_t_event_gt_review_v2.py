"""Native Event GT GUI launcher, separate from identity localization."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
for path in (root / 'src', root / 'artifacts/pass_i/runtime/vendor',
             root / 'outputs/current_development/video_event_experiment/.deps'):
    sys.path.insert(0, str(path))
from memory_graph.pass_t.phase2a_v2.cli import main

if __name__ == '__main__':
    sys.argv.insert(1, 'gui')
    main()
