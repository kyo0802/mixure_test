"""Coarse load observer, no generation text or private reasoning retained."""
import json
import sys
import time
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v294_strata.resources import ResourceMonitor
from memory_graph.v294_strata.runner import OUT, save

started = time.monotonic(); health = None
with ResourceMonitor() as monitor:
    while time.monotonic()-started < 600:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2) as r:
                candidate = json.loads(r.read())
            if candidate.get('loaded'):
                health = candidate
                break
        except Exception:
            pass
        time.sleep(3)
save(OUT/'setup/load_metrics.json', {'elapsed_seconds': time.monotonic()-started,
                                    'health': health, 'resources': monitor.summary(), 'loaded': health is not None})
print('Loaded:', health, 'seconds:', time.monotonic()-started, flush=True)
raise SystemExit(0 if health is not None else 1)
