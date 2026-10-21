"""Small durable CPU-side boundary trace; deliberately excludes paths/content."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import time


class Trace:
    def __init__(self, path, revision=None):
        self.path=Path(path); self.start=time.monotonic(); self.revision=revision

    def event(self, stage, *, seconds=None, **fields):
        row=dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(),
            elapsed_s=time.monotonic()-self.start, seconds=seconds, pid=os.getpid(),
            runtime=platform.system()+'/'+platform.python_version(), revision=self.revision, **fields)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a',encoding='utf8') as f: f.write(json.dumps(row)+'\n'); f.flush()
        return row

    @contextmanager
    def span(self, stage, **fields):
        start=time.monotonic(); self.event(stage+'_start', **fields)
        try: yield
        except BaseException:
            self.event(stage, seconds=time.monotonic()-start, outcome='FAILED', **fields); raise
        else: self.event(stage, seconds=time.monotonic()-start, outcome='COMPLETE', **fields)
