"""Authenticated app-server transport for isolated visual-only model requests."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
import tomllib
from pathlib import Path

from .common import ROOT, OUT, write, sha
from .adapter import build_request
from .pilot import MODEL, PROMPT_FILE, PILOT_OUT

DISABLED = ['apps', 'browser_use', 'browser_use_external', 'computer_use', 'in_app_browser',
            'shell_tool', 'unified_exec', 'view_image', 'multi_agent', 'multi_agent_v2',
            'code_mode', 'code_mode_host', 'skill_search', 'workspace_dependencies',
            'goals', 'sleep_tool']
CONFIG = {**{f'features.{k}': False for k in DISABLED},
          'features.skip_host_skill_discovery': True, 'project_doc_max_bytes': 0,
          'web_search': 'disabled', 'developer_instructions': '', 'model_reasoning_effort': 'high',
          'model': MODEL}


def turn_input(item, prompt):
    request = build_request(item, prompt)
    content = request['input'][1]['content']
    return [{'type': 'text', 'text': c['text']} if c['type'] == 'input_text' else
            {'type': 'image', 'url': c['image_url'], 'detail': 'high'} for c in content]


class CodexTransport:
    def __init__(self, output_dir=PILOT_OUT):
        self.q = queue.Queue()
        self.counter = 0
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workspace = OUT / 'runtime/pilot_empty_workspace'
        self.workspace.mkdir(parents=True, exist_ok=True)
        executable = shutil.which('codex')
        if not executable:
            raise FileNotFoundError('Authenticated Codex executable unavailable')
        args = [executable, 'app-server', '--stdio']
        config = dict(CONFIG)
        # Disable explicit MCP servers from the user config without disclosing values.
        config_file = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'config.toml'
        if config_file.exists():
            with config_file.open('rb') as f:
                user = tomllib.load(f)
            for name in user.get('mcp_servers', {}):
                config[f'mcp_servers.{name}.enabled'] = False
        for key, value in config.items():
            args += ['-c', key + '=' + json.dumps(value)]
        self.events = self.output_dir / 'transport_events.jsonl'
        self.stderr = (self.output_dir / 'transport_stderr.log').open('a', encoding='utf-8')
        self.proc = subprocess.Popen(args, cwd=self.workspace, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, text=True, encoding='utf-8', bufsize=1)
        def reader():
            with self.events.open('a', encoding='utf-8') as f:
                for line in self.proc.stdout:
                    f.write(line); f.flush()
                    try:
                        self.q.put(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                self.q.put({'transport_closed': self.proc.poll()})
        threading.Thread(target=reader, daemon=True).start()
        self.initialized = self.rpc('initialize', {'clientInfo': {'name': 'findmind_pass_i_dev_pilot', 'version': '1.0'},
                                                  'capabilities': {'experimentalApi': True}})
        self.notify('initialized', {})
        write(self.output_dir / 'transport_configuration.json', {'model': MODEL, 'configuration': config,
              'codex_path': executable, 'initialize': self.initialized,
              'instruction_source': 'exact user prompt via thread/start.baseInstructions',
              'ephemeral': True, 'tool_calls_allowed': False, 'reasoning_effort': 'high',
              'workspace': str(self.workspace.relative_to(ROOT))})

    def notify(self, method, params):
        self.proc.stdin.write(json.dumps({'method': method, 'params': params}) + '\n')
        self.proc.stdin.flush()

    def rpc(self, method, params, timeout=120):
        self.counter += 1
        ident = self.counter
        self.proc.stdin.write(json.dumps({'id': ident, 'method': method, 'params': params}) + '\n')
        self.proc.stdin.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            event = self.q.get(timeout=max(.1, deadline - time.monotonic()))
            if event.get('id') == ident:
                if 'error' in event:
                    raise RuntimeError(event['error'])
                return event['result']
            if 'transport_closed' in event:
                raise RuntimeError('App-server closed: ' + str(event))
        raise TimeoutError(method)

    def infer(self, item, timeout=600):
        prompt = PROMPT_FILE.read_text(encoding='utf-8')
        inputs = turn_input(item, prompt)
        # Request audit intentionally records sanitized transport, not hidden manifests.
        audit = self.output_dir / 'requests' / f"{item['item_id']}.json"
        if audit.exists():
            raise FileExistsError('Request already attempted; no silent retries')
        params = {'model': MODEL, 'modelProvider': 'openai', 'cwd': str(self.workspace),
                  'approvalPolicy': 'never', 'sandbox': 'read-only', 'baseInstructions': prompt,
                  'developerInstructions': '', 'ephemeral': True, 'config': CONFIG}
        write(audit, {'schema': 'pass_i_actual_transport_request_v1', 'thread_start': params,
                      'turn_input': inputs, 'prompt_sha256': sha(PROMPT_FILE)})
        start = time.perf_counter()
        thread = self.rpc('thread/start', params)
        if thread.get('model') != MODEL:
            raise RuntimeError('Requested model was substituted')
        tid = thread['thread']['id']
        self.rpc('turn/start', {'threadId': tid, 'model': MODEL, 'effort': 'high', 'input': inputs,
                               'cwd': str(self.workspace)})
        messages, raw_events = {}, []
        deadline = time.monotonic() + timeout
        status, error = None, None
        while time.monotonic() < deadline:
            event = self.q.get(timeout=max(.1, deadline - time.monotonic()))
            raw_events.append(event)
            method, params = event.get('method', ''), event.get('params', {})
            if 'id' in event and 'method' in event:
                # Reject any permission/tool/elicitation request; never provide metadata.
                self.proc.stdin.write(json.dumps({'id': event['id'], 'error': {'code': -32601, 'message': 'Tools are unavailable in this visual-only pilot'}}) + '\n')
                self.proc.stdin.flush()
            if method == 'item/started' and params.get('item', {}).get('type') in {'commandExecution', 'fileChange', 'mcpToolCall', 'webSearch', 'dynamicToolCall'}:
                self.rpc('turn/interrupt', {'threadId': tid, 'turnId': params['turnId']})
                raise RuntimeError('Visual-only boundary violated: model attempted a tool')
            if method == 'item/completed':
                m = params.get('item', {})
                if m.get('type') == 'agentMessage':
                    messages[m['id']] = m.get('text', '')
            if method == 'turn/completed' and params.get('threadId') == tid:
                turn = params['turn']; status = turn['status']; error = turn.get('error')
                break
            if 'transport_closed' in event:
                raise RuntimeError('Transport closed during inference')
        if status is None:
            raise TimeoutError('Model turn timed out')
        text = '\n'.join(messages.values())
        runtime = {'wall_seconds': time.perf_counter() - start, 'model': thread['model'], 'model_revision': None,
                   'thread_id': tid, 'turn_status': status, 'turn_error': error, 'tool_calls': 0,
                   'request_sha256': sha(audit), 'transport': 'codex_app_server'}
        return {'thread_start_result': thread, 'events': raw_events}, text, runtime

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except (subprocess.TimeoutExpired, OSError):
            self.proc.terminate()
        self.stderr.close()
