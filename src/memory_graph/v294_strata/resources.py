"""Coarse resource sampling; page faults include soft faults, not paging proof."""
import ctypes
import subprocess
import threading
import time

import psutil


def sample():
    m = psutil.virtual_memory()
    result = {'unix': time.time(), 'ram_used_bytes': m.used, 'ram_available_bytes': m.available,
              'ram_total_bytes': m.total}
    try:
        proc = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.free', '--format=csv,noheader,nounits'],
                              capture_output=True, text=True, timeout=5,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        used, free = [int(x.strip()) for x in proc.stdout.splitlines()[0].split(',')]
        result.update(vram_used_bytes=used*2**20, vram_available_bytes=free*2**20)
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        result['gpu_sampling_error'] = True
    try:
        class PerformanceInfo(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in
                       ('CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
                        'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
                       ('HandleCount', ctypes.c_ulong), ('ProcessCount', ctypes.c_ulong), ('ThreadCount', ctypes.c_ulong)]
        p = PerformanceInfo(); p.cb = ctypes.sizeof(p)
        if ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(p), p.cb):
            result.update(commit_bytes=p.CommitTotal*p.PageSize, commit_limit_bytes=p.CommitLimit*p.PageSize)
    except AttributeError:
        pass
    return result


class ResourceMonitor:
    def __init__(self, interval=2):
        self.interval = interval
        self.samples = []
        self.stop = threading.Event()

    def _run(self):
        while not self.stop.is_set():
            self.samples.append(sample())
            self.stop.wait(self.interval)

    def __enter__(self):
        self.samples.append(sample())
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set(); self.thread.join(timeout=7)
        self.samples.append(sample())

    def summary(self):
        return {'samples': len(self.samples),
                'ram_before_bytes': self.samples[0]['ram_used_bytes'],
                'peak_system_ram_used_bytes': max(x['ram_used_bytes'] for x in self.samples),
                'min_system_ram_available_bytes': min(x['ram_available_bytes'] for x in self.samples),
                'peak_global_vram_used_bytes': max((x.get('vram_used_bytes', 0) for x in self.samples), default=0),
                'peak_system_commit_bytes': max((x.get('commit_bytes', 0) for x in self.samples), default=0),
                'paging_measurement': 'Commit and available RAM only; page-in/out counters unavailable. No direct SSD paging-rate measurement.',
                'timeline': self.samples}
