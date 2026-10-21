"""Read-only session discovery and integrity checks. No inference imports."""
import json
from pathlib import Path
import re
from memory_graph.integration.adapters import sha


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def session_path(root, identifier):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',identifier):raise ValueError('Invalid session identifier')
    base=(Path(root)/'artifacts/findmind_sessions').resolve()
    path=(base/identifier).resolve()
    if path.parent!=base or not path.is_dir():raise ValueError('Session outside approved directory or unavailable')
    return path


def load_session(root, identifier):
    path=session_path(root,identifier)
    manifest=read(path/'source_manifest.json');receipt=read(path/'run_receipt.json')
    if sha(path/'source_manifest.json')!=receipt['manifest_sha256']:raise ValueError('Session manifest hash mismatch')
    if sha(path/'memory_graph.json')!=receipt['graph_sha256']:raise ValueError('Session Graph hash mismatch')
    if receipt.get('session_id')!=identifier:raise ValueError('Session receipt identity mismatch')
    return path,manifest,receipt


def discover_sessions(root):
    base=Path(root)/'artifacts/findmind_sessions';rows=[]
    if not base.exists():return rows
    for p in base.iterdir():
        if not p.is_dir():continue
        try:
            path=session_path(root,p.name);m=read(path/'source_manifest.json')
            r=read(path/'run_receipt.json') if (path/'run_receipt.json').exists() else None
            graph=(path/'memory_graph.json').is_file()
            partial=bool(r and (r.get('assembly_errors') or any(s['status']!='COMPLETE' for s in r['stages'])))
            label=m['video']['original_filename']
            upload=Path(root)/'artifacts/findmind_uploads'/(m['video']['source_sha256']+'.json')
            if upload.exists():label=read(upload).get('filename',label)
            rows.append(dict(id=p.name,label=label,created=m.get('created_utc'),
                status='PARTIAL' if partial else 'COMPLETED' if r and graph else 'PROCESSING',
                graph=graph,queryable=bool(r and graph),evidence=any((path/'evidence/source').glob('*.png')),
                duration=m['video'].get('presentation_duration_s'),source_sha256=m['video']['source_sha256']))
        except (ValueError,KeyError,OSError,json.JSONDecodeError):continue
    return sorted(rows,key=lambda x:x.get('created') or '',reverse=True)


def enrolled_entities(root, identifier):
    path,_,_=load_session(root,identifier)
    g=read(path/'memory_graph.json')
    return sorted({o['authorized_entity_id'] for o in g['metadata']['observations']
        if o.get('authorized_entity_id') and o.get('identity_authorization')})
