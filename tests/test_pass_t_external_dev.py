"""Synthetic external returns only; original schema and semantics are reused."""
import copy
import io
import json
import stat
import struct
import uuid
import zipfile
from pathlib import Path
import pytest
from test_pass_t_phase2a_v2 import synthetic, confirmed, coverage
from memory_graph.pass_t.phase2a_v2 import policy, validation
from memory_graph.pass_t.external_dev.authority import Authority
from memory_graph.pass_t.external_dev.security import Blocked, digest, json_bytes, parse_archive, strict_json, safe_path
from memory_graph.pass_t.external_dev.audit import audit, dataset_view, RECONCILE
from memory_graph.pass_t.external_dev.store import import_archive, verify_import, finalize, inventory, checked_root


@pytest.fixture
def tmp_path(tmp_path_factory):
    return checked_root(tmp_path_factory.mktemp('external'))


@pytest.fixture
def fixture(synthetic):
    f = synthetic
    manifest = {'items': [f['entry']], 'repeat_subset': [f['item']['annotation_item_id']]}
    f['authority'] = Authority(f['receipt'], manifest, json_bytes(manifest), b'{"frozen":true}', b'{"release":true}',
        {f['item']['annotation_item_id']: f['item']}, {f['item']['annotation_item_id']: f['backend']}, {'synthetic': True})
    return f


def members(f, response=None):
    r = copy.deepcopy(response or f['response'])
    name = f"responses/{r['annotation_item_id']}_r{r['review_round']}.json"
    raw = json_bytes(r)
    result = validation.validate(r, f['item'], f['entry']['item_sha256'], f['receipt'], f['backend'])
    proof = {'response_sha256': digest(raw), 'response_path': name, **result,
             'evaluation': validation.evaluation_metadata(r, result)}
    data = {name: raw, 'validated/' + r['provenance']['submission_id'] + '.json': json_bytes(proof),
            'release_receipt.json': f['authority'].release_raw, 'manifest.freeze.json': f['authority'].freeze_raw}
    return update_manifest(f, data)


def update_manifest(f, data):
    data['return_manifest.json'] = json_bytes({'schema_version': 'PASS_T_ANNOTATION_RETURN_V1',
        'release_receipt_sha256': digest(data.get('release_receipt.json', b'')),
        'source_manifest_sha256': digest(f['authority'].manifest_raw), 'policy_md_sha256': f['receipt']['policy_md_sha256'],
        'formal_eligible': 0, 'binding_causality_status': 'CAUSALITY_UNVERIFIED',
        'files_sha256': {n: digest(b) for n, b in data.items() if n.startswith(('responses/', 'validated/'))}})
    return data


def archive(tmp_path, data, compression=zipfile.ZIP_STORED):
    path = tmp_path / (uuid.uuid4().hex + '.zip')
    with zipfile.ZipFile(path, 'w', compression=compression) as z:
        for name, raw in data.items(): z.writestr(name, raw)
    return path, digest(path.read_bytes())


def run_audit(f, tmp_path, data=None):
    p, sha = archive(tmp_path, data or members(f))
    return audit(parse_archive(p, sha), f['authority'])


def test_ingestion_idempotence_readonly_preservation(fixture, tmp_path):
    f = fixture; root = tmp_path / 'external'
    protected = {p: p.read_bytes() for p in f['out'].rglob('*') if p.is_file()}
    canonical = sorted((policy.OUT/'responses').glob('*'))
    p, sha = archive(tmp_path, members(f)); original = p.read_bytes()
    assert import_archive(p, sha, root, f['authority'])['status'] == 'IMPORTED'
    before = {n: n.read_bytes() for n in root.rglob('*') if n.is_file()}
    assert import_archive(p, sha, root, f['authority'])['status'] == 'ALREADY_IMPORTED'
    assert all(n.read_bytes() == b for n, b in before.items())
    result = finalize(root, f['authority'])
    assert not Path(result['path']).stat().st_mode & stat.S_IWRITE
    assert result == finalize(root, f['authority'])
    assert result['summary']['formal_eligible'] == 0
    assert p.read_bytes() == original
    assert all(n.read_bytes() == b for n, b in protected.items())
    assert sorted((policy.OUT/'responses').glob('*')) == canonical


def test_wrong_sha(fixture, tmp_path):
    p, _ = archive(tmp_path, members(fixture))
    with pytest.raises(Blocked, match='SHA256_MISMATCH'): parse_archive(p, '0'*64)


def test_crc(fixture, tmp_path):
    p, _ = archive(tmp_path, members(fixture)); raw = bytearray(p.read_bytes())
    namelen, extralen = struct.unpack_from('<HH', raw, 26)
    raw[30 + namelen + extralen + 4] ^= 1
    p.write_bytes(raw)
    with pytest.raises(Blocked, match='CRC'): parse_archive(p, digest(raw))


@pytest.mark.parametrize('name', ['release_receipt.json', 'manifest.freeze.json', 'return_manifest.json'])
def test_missing_mandatory(fixture, tmp_path, name):
    data = members(fixture); del data[name]; p, sha = archive(tmp_path, data)
    with pytest.raises(Blocked, match='MISSING'): parse_archive(p, sha)


@pytest.mark.parametrize('name', ['../evil.json', '/evil.json', 'C:/evil.json', 'a\\evil.json', 'evil.exe', 'responses/extra.json'])
def test_unsafe_names(fixture, tmp_path, name):
    data = members(fixture); data[name] = b'{}'; p, sha = archive(tmp_path, data)
    with pytest.raises(Blocked): parse_archive(p, sha)


def test_case_collision(fixture, tmp_path):
    data = members(fixture); data['RELEASE_RECEIPT.JSON'] = b'{}'; p, sha = archive(tmp_path, data)
    with pytest.raises(Blocked, match='COLLISION'): parse_archive(p, sha)


def test_symlink(fixture, tmp_path):
    p, _ = archive(tmp_path, members(fixture))
    with zipfile.ZipFile(p, 'a') as z:
        info = zipfile.ZipInfo('validated/' + str(uuid.uuid4()) + '.json')
        info.create_system = 3; info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, 'somewhere')
    with pytest.raises(Blocked, match='UNSAFE_FILE_TYPE'): parse_archive(p, digest(p.read_bytes()))


@pytest.mark.parametrize('raw', [b'{', b'{"a":1,"a":2}', b'{"n":NaN}', b'{"n":Infinity}', b'{"n":1e999}', b'[]'])
def test_json_rejection(raw):
    with pytest.raises(Blocked): strict_json(raw)


def test_decompression(fixture, tmp_path):
    data = members(fixture); data['release_receipt.json'] = json_bytes({'data': 'a'*1000000})
    p, sha = archive(tmp_path, data, zipfile.ZIP_DEFLATED)
    with pytest.raises(Blocked, match='DECOMPRESSION'): parse_archive(p, sha)


def test_hash_tamper(fixture, tmp_path):
    data = members(fixture); data[next(n for n in data if n.startswith('responses/'))] += b' '
    p, sha = archive(tmp_path, data)
    with pytest.raises(Blocked, match='HASH_MISMATCH'): parse_archive(p, sha)


@pytest.mark.parametrize('kind', ['source_manifest_sha256', 'policy_md_sha256', 'schema_version'])
def test_metadata_incompatible(fixture, tmp_path, kind):
    data = members(fixture); m = strict_json(data['return_manifest.json']); m[kind] = 'wrong'
    data['return_manifest.json'] = json_bytes(m)
    with pytest.raises(Blocked): run_audit(fixture, tmp_path, data)


def test_altered_receipt_quarantined(fixture, tmp_path):
    data = members(fixture); key = next(n for n in data if n.startswith('validated/'))
    proof = strict_json(data[key]); proof['valid'] = False; data[key] = json_bytes(proof)
    r = run_audit(fixture, tmp_path, update_manifest(fixture, data))['records'][0]
    assert r['schema_valid'] and r['semantic_valid'] and not r['valid']
    assert r['category'] == 'QUARANTINED_INVALID'


def test_missing_response_receipt_quarantined(fixture, tmp_path):
    data = members(fixture); del data[next(n for n in data if n.startswith('validated/'))]
    r = run_audit(fixture, tmp_path, update_manifest(fixture, data))['records'][0]
    assert r['category'] == 'QUARANTINED_INVALID'


def test_unreferenced_receipt_blocked(fixture, tmp_path):
    data = members(fixture); data['validated/' + str(uuid.uuid4()) + '.json'] = b'{}'
    with pytest.raises(Blocked, match='UNREFERENCED'):
        run_audit(fixture, tmp_path, update_manifest(fixture, data))


def test_same_archive_reviewer_spelling_pending(fixture, tmp_path):
    from memory_graph.pass_t.phase2a_v2.storage import attach_backend
    f = fixture; data = members(f)
    item = copy.deepcopy(f['item']); item['annotation_item_id'] = 'PT2A_' + 'd'*16
    entry = copy.deepcopy(f['entry']); entry['annotation_item_id'] = item['annotation_item_id']; entry['item_sha256'] = policy.object_sha(item)
    f['authority'].manifest['items'].append(entry)
    f['authority'].manifest_raw = json_bytes(f['authority'].manifest)
    f['authority'].items[item['annotation_item_id']] = item
    f['authority'].backends[item['annotation_item_id']] = f['backend']
    draft = copy.deepcopy(f['draft']); draft['reviewer_id'] = 'SYNTHETIC_REVEIWER'
    r = attach_backend(draft,item,entry,f['backend'],f['receipt'],1)
    f2 = {**f, 'item': item, 'entry': entry}
    data.update({n:b for n,b in members(f2,r).items() if n.startswith(('responses/','validated/'))})
    result = run_audit(f,tmp_path,update_manifest(f,data))
    assert result['summary']['independently_valid'] == 2
    assert all(RECONCILE in r['human_review_flags'] for r in result['records'])


def test_invalid_phase1c_item(fixture, tmp_path):
    value = copy.deepcopy(fixture['response']); value['annotation_item_id'] = 'PT2A_' + 'f'*16
    r = run_audit(fixture, tmp_path, members(fixture, value))['records'][0]
    assert not r['valid'] and r['category'] == 'QUARANTINED_INVALID'


@pytest.mark.parametrize('kind,category,full', [('positive','ACCEPTED_EXPLORATORY_POSITIVE',False),
    ('negative','ACCEPTED_STRICT_NEGATIVE',True), ('unknown','ACCEPTED_UNCERTAIN',False),
    ('exposure','QUARANTINED_EXCLUDED',False)])
def test_classification(fixture, tmp_path, kind, category, full):
    value = copy.deepcopy(fixture['response'])
    if kind == 'positive': value = confirmed(fixture)
    if kind == 'negative': value['window_outcome'] = 'NO_CONFIRMED_EVENT'; coverage(value)
    if kind == 'exposure': value['attestations']['model_predictions_viewed'] = True
    r = run_audit(fixture, tmp_path, members(fixture, value))['records'][0]
    assert r['valid'], r['independent_validation']
    assert r['category'] == category
    assert r['evaluation']['full_window_event_evaluation_supported'] is full
    if kind == 'positive':
        assert r['evaluation']['unlisted_events_status'] == 'UNEVALUATED'
        assert r['human_review_pending'] and not r['quality_cleared_for_model_scoring']


def test_multi_reviewer_same_window_and_conflict(fixture, tmp_path):
    f = fixture; root = tmp_path/'external'
    p, sha = archive(tmp_path, members(f)); import_archive(p, sha, root, f['authority'])
    r = confirmed(f); r['reviewer_id'] = 'SYNTHETIC_REVEIWER'; r['same_reviewer_as_phase1c'] = False
    r['provenance']['submission_id'] = str(uuid.uuid4())
    p2, sha2 = archive(tmp_path, members(f,r)); import_archive(p2, sha2, root, f['authority'])
    result = finalize(root, f['authority']); data = strict_json(Path(result['path']).read_bytes())
    assert len(data['records']) == 2 and data['reviewer_comparisons'][0]['structured_answers_differ']
    assert all(RECONCILE in a['human_review_flags'] and 'ADJUDICATION_PENDING' in a['human_review_flags'] for a in data['records'])
    assert {a['reviewer_id'] for a in data['records']} == {'SYNTHETIC_REVIEWER','SYNTHETIC_REVEIWER'}
    assert all(a['review_round'] == 1 for a in data['records'])
    assert import_archive(p, sha, root, f['authority'])['status'] == 'ALREADY_IMPORTED'


def test_duplicate_submission_quarantined(fixture, tmp_path):
    f = fixture; root = tmp_path/'external'; p, sha = archive(tmp_path, members(f))
    import_archive(p, sha, root, f['authority'])
    r = confirmed(f); p2, sha2 = archive(tmp_path, members(f,r))
    result = import_archive(p2,sha2,root,f['authority'])
    assert result['audit']['records'][0]['category'] == 'QUARANTINED_INVALID'
    assert 'SUBMISSION_ID_REUSED_ACROSS_ARCHIVES' in result['audit']['records'][0]['independent_validation']['errors']


@pytest.mark.parametrize('kind',['raw','derived','partial'])
def test_existing_conflict_blocks(fixture, tmp_path, kind):
    f = fixture; root = tmp_path/'external'; p, sha = archive(tmp_path, members(f))
    if kind == 'partial': (root/sha).mkdir(parents=True)
    else:
        import_archive(p,sha,root,f['authority'])
        target = next((root/sha/('original_responses' if kind == 'raw' else 'independent_validation')).glob('*.json'))
        target.chmod(stat.S_IREAD | stat.S_IWRITE); target.write_bytes(b'{}'); target.chmod(stat.S_IREAD)
        # Even updating the local completion file hash cannot bless changed derived records.
        receipt_path = root/sha/'completion_receipt.json'; receipt = strict_json(receipt_path.read_bytes())
        receipt['files_sha256'][target.relative_to(root/sha).as_posix()] = digest(b'{}')
        receipt_path.chmod(stat.S_IREAD | stat.S_IWRITE); receipt_path.write_bytes(json_bytes(receipt)); receipt_path.chmod(stat.S_IREAD)
    with pytest.raises(Blocked): import_archive(p,sha,root,f['authority'])


def test_no_inference_or_graph_dependencies():
    import ast
    root = Path(__file__).resolve().parents[1]/'src/memory_graph/pass_t/external_dev'
    for path in root.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import): names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom): names = [node.module or '']
            else: continue
            assert not any(x in n.lower() for n in names for x in ('torch','openai','transformers','inference','graph_writer'))


def test_report_nullable_coverage_description(fixture, tmp_path):
    from memory_graph.pass_t.external_dev.reporting import markdown
    result = run_audit(fixture,tmp_path,members(fixture,confirmed(fixture)))
    result['records'][0]['authorized_frame_checklist'][0]['annotation_description'] = None
    assert '(未提供文字描述)' in markdown(result)
