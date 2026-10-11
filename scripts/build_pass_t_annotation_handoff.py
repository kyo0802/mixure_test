"""Owner-only allowlisted snapshot builder; never overwrite a released package."""
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_t.phase2a_v2.policy import OUT, CONTRACTS, read, sha, within, object_sha, verify_gate, utc

BUNDLE = ROOT / 'annotation_handoff/pass_t_phase2a_v2'
TEMPLATES = {'.gitignore', 'README.md', 'requirements.txt', 'review.py',
             'Start_Annotation.cmd', 'Return_Annotations.cmd'}


def build():
    if (BUNDLE / 'release_receipt.json').exists() or not {p.name for p in BUNDLE.iterdir()} <= TEMPLATES | {'src', 'artifacts'}:
        raise ValueError('DESTINATION_NOT_TEMPLATE_ONLY; existing release is never overwritten')
    receipt = verify_gate()
    manifest = read(OUT / 'manifest.json')
    if sha(OUT / 'manifest.json') != read(OUT / 'manifest.freeze.json')['manifest_sha256']:
        raise ValueError('SOURCE_MANIFEST_CHANGED')
    sources = {}

    def include(source, relative):
        source = within(ROOT, source)
        target = within(BUNDLE, relative)
        digest = sha(source)
        if target.exists():
            if sha(target) != digest:
                raise ValueError('CHANGED_PARTIAL_BUILD_FILE: ' + relative)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst)
        if sha(target) != digest:
            raise ValueError('COPY_HASH_MISMATCH')
        sources[relative] = digest

    for name in ('__init__.py', 'policy.py', 'projection.py', 'validation.py', 'storage.py',
                 'finalize.py', 'viewer.py', 'cli.py'):
        path = 'src/memory_graph/pass_t/phase2a_v2/' + name
        include(path, path)
    for path in ('src/memory_graph/__init__.py', 'src/memory_graph/pass_t/__init__.py'):
        include(path, path)
    outrel = OUT.relative_to(ROOT).as_posix()
    for name in list(receipt['files_sha256']) + ['EVENT_GT_POLICY_V2.freeze_receipt.json']:
        include(CONTRACTS / name, outrel + '/contracts/' + name)
    for name in ('manifest.json', 'manifest.freeze.json', 'stage_b/approval.json'):
        include(OUT / name, outrel + '/' + name)
    images = {}
    frames = references = 0
    item_hashes = {}
    for entry in manifest['items']:
        source = within(OUT, entry['item_path'])
        if sha(source) != entry['item_sha256']:
            raise ValueError('SOURCE_ITEM_CHANGED')
        item = read(source)
        if object_sha(item['visual']) != item['authorized_visual_manifest_sha256']:
            raise ValueError('SOURCE_VISUAL_AUTHORIZATION_CHANGED')
        include(source, outrel + '/' + entry['item_path'])
        private = 'private/' + entry['annotation_item_id'] + '.json'
        backend = read(OUT / private)
        required = {'phase1c_response_sha256', 'phase1c_reviewer_id'}
        if not required <= set(backend) <= required | {'source_review_item_sha256'} or sha(OUT / private) != entry['backend_sha256']:
            raise ValueError('NON_NEUTRAL_OR_CHANGED_BACKEND')
        include(OUT / private, outrel + '/' + private)
        item_hashes[entry['annotation_item_id']] = entry['item_sha256']
        frames += len(item['visual']['frames'])
        references += len(item['visual']['references'])
        allowed = [outrel + '/items/' + entry['annotation_item_id'] + '/frames/']
        allowed += ['artifacts/pass_t/human_seed_review/items/' + pack + '/' for pack in item['original_pack_ids']]
        for row in item['visual']['frames'] + item['visual']['references']:
            name = row['image_path']
            if not name.endswith('.png') or not any(name.startswith(prefix) for prefix in allowed):
                raise ValueError('ASSET_OUTSIDE_AUTHORIZED_ITEM')
            if sha(within(ROOT, name)) != row['sha256']:
                raise ValueError('SOURCE_IMAGE_CHANGED')
            if name in images and images[name] != row['sha256']:
                raise ValueError('ASSET_HASH_COLLISION')
            images[name] = row['sha256']
    for name in sorted(images):
        include(name, name)
    immutable = {**sources, **{name: sha(BUNDLE / name) for name in TEMPLATES}}
    if {p.relative_to(BUNDLE).as_posix() for p in BUNDLE.rglob('*') if p.is_file()} != set(immutable):
        raise ValueError('UNAUTHORIZED_EXTRA_FILES_IN_HANDOFF')
    baseline = outrel + '/stage_b/protected_before.json'
    with (BUNDLE / baseline).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(immutable, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    immutable[baseline] = sha(BUNDLE / baseline)
    release = {'schema_version': 'PASS_T_ANNOTATION_HANDOFF_V1', 'created_at_utc': utc(),
               'authorization': 'Direct user request: 先push上去一版 我要可以讓別人幫我做完標註的',
               'policy_md_sha256': receipt['policy_md_sha256'],
               'source_manifest_sha256': sha(OUT / 'manifest.json'), 'source_item_sha256': item_hashes,
               'windows': len(manifest['items']), 'frames': frames, 'references': references,
               'source_video_files': len({e['source_video_identifier'] for e in manifest['items']}),
               'nonoverlap_groups': len({e['overlap_group_id'] for e in manifest['items']}),
               'authorized_image_bytes': sum((BUNDLE / name).stat().st_size for name in images),
               'responses_at_release': 0, 'formal_eligible': 0,
               'preservation_scope': 'Standalone handoff subtree only; not a replacement for the original full-project baseline.',
               'source_code': 'Byte-identical Stage B snapshot; no policy/schema/item/visual changes.',
               'excluded_material': ['Frozen', 'source videos', 'models', 'environments', 'human answers',
                                     'model event outputs', 'scores', 'aliases', 'physical GT'],
               'files_sha256': immutable}
    with (BUNDLE / 'release_receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(release, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in release.items() if key not in ('files_sha256', 'source_item_sha256')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
