"""Read-only legacy audit and pre-change preservation snapshot."""
from pathlib import Path
import hashlib, json, time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/identity_rebuild'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()
def write(p, x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')

PATHS = [
('v25rerun/binding.py','TargetBinding.bind_target','causal initial observation/tracklet','BoundTarget phone_01 proposal','selector only','none','no','source track/frame'),
('v23/fusion.py','EntityRegistry.observe_sam','inherited SAM object ID','sam_to_entity; propagated history','drift only','none','no','SAM local ID, no epoch'),
('v23/fusion.py','EntityRegistry.observe_yolo','existing local mapping OR SAM IoU >= .30','track_to_entity; trusted history','NO central guard','none','no','local track and overlap'),
('v23/fusion.py','EntityRegistry.confirm_raw_yolo','raw phone class and exactly one SAM IoU >= .30','trusted phone_01 observation','NO central guard','none','no','raw frame and SAM overlap'),
('v23/fusion.py','EntityRegistry._attach','caller entity ID/trusted boolean','last trusted time and source lists','caller boolean','none','no','observation source'),
('v25rerun/fusion.py','fuse_video','V21 groups, YOLO, SAM','legacy registry, timeline','delegates unsafe V23','none','no','frozen inputs'),
('v24/appearance.py','AppearanceBank.add','caller trusted boolean','permanent prototypes','boolean only','embedding','no','frame and caller reason'),
('v25rerun/reid.py','bank_at_frame','legacy trusted track + accepted SAM','trusted bank prototypes','legacy trust','MobileNet vector','no','crop/cache key'),
('v24/reid.py','decide','one selected candidate crop vs bank','MATCH recommendation','similarity .60/margin .10','max prototype; candidate ranking','not a write','scored audit'),
('v24/reid.py','registry_update','MATCH string','query history, sources, bank','string only','single candidate view','no','candidate history'),
('v25rerun/reid.py','run_reid','MATCH result','registry aliases; SAM restart','legacy decision','single view','no','attempt record'),
('v26/authorization.py','authorize','scored current candidate','CONFIRMED_MATCH and write booleans','.60/.10 and current presence','no multi-time persistence','no','V26 decision'),
('v26/pipeline.py','run_video','first CONFIRMED_MATCH','registry_update, aliases, reinitialize','V26 guard; fusion bypass still exists','single selected crop','no','candidate and attempt'),
('v25rerun/sam_route.py','SamRouter.target / reinitialize_after_match','BoundTarget / candidate','target SAM seed and inherited target log','caller controls invocation','none at sink','no','seed detection'),
('v292/pipeline.py','_canonical_identity','legacy timeline and V26 confirms','canonical authorizations and identity states','wraps earlier decisions','inherited evidence','no','legacy source'),
('v292/pipeline.py','_store_masks / _reconcile_forward_timeline','legacy visible states and reinit log','trusted mask references / forward MATCHED','inherited binding fallback','none','no','mask file'),
('v292/pipeline.py','_update_future_appearance_bank','authorized reinitialized masks','12 val_9 forward bank updates','inherits false confirmation','new vectors but contaminated parent','no','frame/authorization, no revocation cascade'),
('v292/pipeline.py','_identity_memory_frames','registry/timeline/masks','trusted memory observations','legacy state','none','no','source IDs'),
('events/development_sources.py','authorized_rows','V292 identity and V293 recovered rows','builder trusted target rows','legacy trust imported','none','no','chain label only'),
('validation/upstream.py','run','raw perception -> V23/V26/V292','all above writes in validation IO root','same bypasses','same gates','no','run manifest'),
('validation/evidence.py','authorized_rows','validation legacy identity','builder trusted target rows','legacy trust imported','none','no','source IDs'),
]

def main():
    dest=OUT/'audit/prechange_manifest.json'
    if dest.exists(): raise RuntimeError('Preservation snapshot already exists')
    records=[]
    for module,fn,inp,mutation,guard,appearance,reversible,provenance in PATHS:
        records.append(dict(module='src/memory_graph/'+module,function=fn,input=inp,mutation=mutation,
            guard=guard,appearance=appearance,reversible=reversible,provenance=provenance))
    write(OUT/'audit/IDENTITY_WRITE_PATH_AUDIT.json',{'created_unix':time.time(),'paths':records,
        'val_5_and_val_10':'SAM inherited phone_01 after gap; raw YOLO overlap marked trusted; new track then bound to same persistent entity without appearance/epoch guard.',
        'val_9':'V26 single-view similarity .7286765575 and margin .1629049778 passed; immediate alias/reinit caused 12 forward bank updates.',
        'margin':'Legacy comparison ranks candidate IDs, not bank prototypes, but candidate grouping does not guarantee distinct physical entities.'})
    lines=['# Identity write-path audit','', 'Audit completed before identity implementation. All legacy files remain frozen.','',
        '| Module / function | Input | Mutation | Guard | Appearance | Reversible | Provenance |','|---|---|---|---|---|---|---|']
    lines += ['| '+ ' | '.join(str(r[k]) for k in ('module','input','mutation','guard','appearance','reversible','provenance'))+' | Function: '+r['function'] for r in records]
    lines += ['', '## Failure mechanisms', '',
        'val_5 and val_10: inherited SAM survives loss; raw phone overlap calls _attach(trusted=True), then observe_yolo binds a new track. The guard is bypassed structurally. Prior unauthorized-MATCHED=0 counted formal guard records and did not prove semantic safety.',
        'val_9: one candidate view passes .60 similarity/.10 margin, immediately merges and seeds target SAM. Twelve descendant bank writes have no reversible lineage.',
        'val_8/val_11: insufficient evidence leaves recovery unresolved; keep this distinct from false merges.',
        '', '## Migration boundary', '',
        'New identity package must consume raw detections/tracks/SAM evidence only. Legacy registry, identity timeline, candidate identity labels and bank trust must not be imported as authority. A new entrypoint will reuse pure perception, frozen builder/render/model APIs; old executable scripts remain clearly marked historical reference.']
    (OUT/'audit/IDENTITY_WRITE_PATH_AUDIT.md').write_text('\n'.join(lines),encoding='utf8')
    files={}
    for folder in ('src','scripts','configs','outputs/validation','outputs_v293','outputs/current_development'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc'}:
                files[p.relative_to(ROOT).as_posix()]=sha(p)
    write(dest,{'created_unix':time.time(),'files':files})
    print('Audited',len(records),'write paths; preserved',len(files),'files')
if __name__=='__main__':main()
