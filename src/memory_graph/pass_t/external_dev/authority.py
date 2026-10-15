"""Original frozen policy, source/Phase1c lineage and authorized media authority."""
from dataclasses import dataclass
from ..phase2a_v2 import policy, projection
from .security import Blocked, strict_json, digest

POLICY_SHA = 'c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4'
MANIFEST_SHA = '1c423256cd31ea0e585b1bc3e57610fc8b215fcbe2757108db3bd96736af9e46'
RELEASE_SHA = '906abe69cae7eb5b0b5fbb7664e5e6fc1e966eda365533b69bb64620c3e6efba'


@dataclass
class Authority:
    receipt: dict
    manifest: dict
    manifest_raw: bytes
    freeze_raw: bytes
    release_raw: bytes
    items: dict
    backends: dict
    verification: dict


def load_authority():
    root, out = policy.ROOT, policy.OUT
    receipt = policy.verify_gate()
    if receipt['policy_md_sha256'] != POLICY_SHA or policy.sha(out/'manifest.json') != MANIFEST_SHA:
        raise Blocked('FROZEN_POLICY_OR_MANIFEST_CHANGED')
    manifest = projection.load_manifest()
    bundle = root/'annotation_handoff/pass_t_phase2a_v2'
    release_raw = (bundle/'release_receipt.json').read_bytes()
    if digest(release_raw) != RELEASE_SHA:
        raise Blocked('AUTHORITATIVE_HANDOFF_RECEIPT_CHANGED')
    release = strict_json(release_raw)
    for name, expected in release['files_sha256'].items():
        if policy.sha(policy.within(bundle, name)) != expected:
            raise Blocked('AUTHORITATIVE_HANDOFF_ASSET_CHANGED: ' + name)
        if name.startswith('src/memory_graph/pass_t/phase2a_v2/') and policy.sha(root/name) != expected:
            raise Blocked('ORIGINAL_PRODUCTION_VALIDATOR_CODE_CHANGED: ' + name)
    pt = root/'artifacts/pass_t'
    mappings = {r['pack_id']: r for r in policy.read(pt/'manifests/window_target_mapping.json')['packs']}
    outcomes = {r['pack_id']: r for r in policy.read(pt/'manifests/human_seed_outcomes_v1.json')['items']}
    lineage = policy.read(pt/'manifests/binding_causal_lineage_v1.json')
    if (policy.sha(pt/'manifests/binding_causal_lineage_v1.json') !=
            '024953d0ae865c4fc3861f79b0b4671f779f3af1c5e79064f664daa792484674'
            or any(p['final_causality_classification'] != 'CAUSALITY_UNVERIFIED' for p in lineage['packs'])):
        raise Blocked('ORIGINAL_BINDING_LINEAGE_CHANGED')
    items, backends, videos = {}, {}, {}
    for entry in manifest['items']:
        id_ = entry['annotation_item_id']
        item = projection.load_item(entry)  # original item, exact visual hash and all authorized assets
        backend = projection.load_backend(entry)
        if release['source_item_sha256'].get(id_) != entry['item_sha256']:
            raise Blocked('HANDOFF_SOURCE_ITEM_LINKAGE')
        for pack in item['original_pack_ids']:
            m = mappings[pack]
            if (m['source_video_hash'] != item['source_video_sha256']
                    or m['authorized_half_open_frames'] != item['authorized_half_open_frames']
                    or m['window_start_s'] != item['window_start_s'] or m['window_end_s'] != item['window_end_s']
                    or m['overlap_group_id'] != item['overlap_group_id']):
                raise Blocked('ORIGINAL_SOURCE_MAPPING_MISMATCH')
            videos[m['source_video_path']] = m['source_video_hash']
            if pack in outcomes:
                o = outcomes[pack]
                if (not o['valid'] or not o['dev_eligible'] or not o['review_completed']
                        or str(o['selected_local_candidate']) != item['selected_local_candidate_id']
                        or o['binding_causality'] != 'CAUSALITY_UNVERIFIED'
                        or o['response_sha256'] != backend['phase1c_response_sha256']
                        or policy.sha(policy.within(pt, o['response_path'])) != o['response_sha256']):
                    raise Blocked('ORIGINAL_PHASE1C_PROVENANCE_MISMATCH')
                original = policy.read(policy.within(pt, o['response_path']))
                if original['primary_response']['annotator_id'] != backend['phase1c_reviewer_id']:
                    raise Blocked('ORIGINAL_REVIEWER_PROVENANCE_MISMATCH')
            elif m['resolution_status'] != 'RESOLVED_UNIQUE' or str(m['resolved_local_track_id']) != item['selected_local_candidate_id']:
                raise Blocked('ORIGINAL_SOURCE_TARGET_UNRESOLVED')
        items[id_], backends[id_] = item, backend
    for name, expected in videos.items():
        if policy.sha(policy.within(root, name)) != expected:
            raise Blocked('ORIGINAL_VIDEO_HASH_MISMATCH')
    if outcomes['test8__W06']['dev_eligible']:
        raise Blocked('ORIGINAL_EXCLUDED_ITEM_PROMOTED')
    return Authority(receipt, manifest, (out/'manifest.json').read_bytes(), (out/'manifest.freeze.json').read_bytes(),
                     release_raw, items, backends,
                     {'frozen_contracts': 'VERIFIED', 'phase1c_provenance': 'VERIFIED',
                      'original_video_hashes_verified': len(videos), 'authorized_items_verified': len(items),
                      'handoff_files_verified': len(release['files_sha256']),
                      'binding_lineage_sha256': policy.sha(pt/'manifests/binding_causal_lineage_v1.json'),
                      'binding_causality_status': 'CAUSALITY_UNVERIFIED', 'formal_eligible': 0})


def compatible(archive, authority):
    values, raw = archive['values'], archive['members']
    m = values['return_manifest.json']
    if raw['release_receipt.json'] != authority.release_raw or raw['manifest.freeze.json'] != authority.freeze_raw:
        raise Blocked('RETURNED_FROZEN_RECEIPT_INCOMPATIBLE')
    if (m.get('source_manifest_sha256') != digest(authority.manifest_raw)
            or m.get('policy_md_sha256') != authority.receipt['policy_md_sha256']
            or m.get('formal_eligible') != 0 or m.get('binding_causality_status') != 'CAUSALITY_UNVERIFIED'):
        raise Blocked('MANDATORY_FROZEN_PROVENANCE_INCOMPATIBLE')
