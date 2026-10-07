"""Evaluation only. Case IDs/labels never enter the identity implementation."""
from pathlib import Path
from dataclasses import asdict
import sys,json,time,re,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.identity.pipeline import ROOT,OUT,read,write,sha,replay,Embedder
from memory_graph.identity.contracts import Policy,digest

def calibration():
    if (OUT/'calibration/confirmation_policy.json').exists():raise FileExistsError('Calibration frozen')
    records=[];sources={}
    for i in range(1,10):
        video=f'test{i}';path=ROOT/f'outputs_v292/{video}/identity/reid_audit.json'
        sources[str(path.relative_to(ROOT))]=sha(path)
        review=ROOT/f'outputs_v26/{video}/review.md';labels={}
        if review.exists():
            sources[str(review.relative_to(ROOT))]=sha(review)
            for line in review.read_text(encoding='utf8').splitlines():
                cells=[x.strip() for x in line.split('|')]
                if len(cells)>7 and cells[1].startswith('candidate_'):
                    labels[(cells[1],int(cells[2]))]=cells[6]
        seen=set()
        for a in read(path)['attempts']:
            for c in a.get('candidate_decisions',[]):
                key=(c['candidate_entity_id'],c['candidate_frame'],c.get('embedding_cache_key'))
                if key in seen:continue
                seen.add(key)
                records.append({'video':video,'candidate_id':key[0],'candidate_frame':key[1],
                    'embedding_cache_key':key[2],'similarity':c['appearance']['max_similarity'],
                    'matrix':c['appearance']['matrix'],'reviewed_identity':labels.get(key[:2],'UNLABELED'),
                    'legacy_decision':c['decision'],'margin':c.get('best_vs_second_margin'),
                    'candidate_views':len(c['appearance']['matrix'])})
    groups={label:[r['similarity'] for r in records if r['reviewed_identity']==label] for label in ('TARGET','DISTRACTOR','UNLABELED')}
    summary={k:{'n':len(v),'min':min(v) if v else None,'max':max(v) if v else None,'mean':sum(v)/len(v) if v else None} for k,v in groups.items()}
    analysis={'source_scope':'PRE-EXISTING DEVELOPMENT ONLY; no val media/GT used for policy',
        'sources':sources,'unique_candidate_view_records':records,'reviewed_distributions':summary,
        'finding':'Sparse reviewed identities and predominantly single selected crops do not calibrate multi-time confirmation. Repeated attempts are not independent observations.',
        'margin_audit':'Old margin ranks candidate IDs; physical uniqueness is not established by multiple prototypes or recycled candidate views.'}
    write(OUT/'calibration/development_similarity_analysis.json',analysis)
    policy=asdict(Policy());write(OUT/'calibration/confirmation_policy.json',{'policy':policy,'policy_sha256':digest(policy),
        'frozen_unix':time.time(),'automatic_confirmation_enabled':False,
        'justification':'No defensible development-only strong numeric threshold. .60/.10 retained for admission; full gates implemented but production stays provisional.',
        'cadence_justification':'.4s = two 5fps sample intervals, matching existing development window gap and initial binding span; 1ms arithmetic tolerance only.',
        'evidence_sha256':sha(OUT/'calibration/development_similarity_analysis.json')})
    text='# Development confirmation calibration\n\n'+json.dumps(summary,indent=2)+'\n\n'
    text+='test7 distractor scores overlap weak true-target scores; test8 f804 is a reviewed correct one-view recovery, not a calibrated distribution. No opened validation labels or scores were used to select policy.\n\n'
    text+='Production long-gap confirmation remains disabled. Synthetic full-evidence tests exercise confirmation and revocation; they do not demonstrate learned real-world separation. Existing thresholds are admission gates only. Initial three causal observations form an immutable core. No automatic quarantine-to-core promotion is deployed.\n'
    (OUT/'calibration/calibration_report.md').write_text(text,encoding='utf8')
    print(summary,flush=True)

def run_set(kind):
    frozen=read(OUT/'calibration/confirmation_policy.json');policy=Policy(**frozen['policy'])
    if digest(asdict(policy))!=frozen['policy_sha256']:raise ValueError('Policy drift')
    if kind=='known_validation_regression' and not (OUT/'development/development_freeze.json').exists():raise RuntimeError('Development first')
    if kind=='known_validation_regression':
        freeze=read(OUT/'development/development_freeze.json')
        if freeze['identity_source_hashes']!=identity_hashes():raise RuntimeError('Code changed after development freeze')
    videos=[f'test{i}' for i in range(1,10)] if kind=='development' else [f'val_{i}' for i in range(1,12)]
    embed=Embedder(OUT/kind/'appearance_cache');results={}
    for v in videos:
        source=ROOT/f'outputs_v292/{v}' if kind=='development' else ROOT/f'outputs/validation/runs/{v}/{v}'
        video=ROOT/f'{v}.mp4' if kind=='development' else ROOT/f'val_set/{v}.mp4'
        out=OUT/kind/'runs_final'/v
        if (out/'metrics.json').exists():
            m=read(out/'metrics.json')
            if m['policy_sha256']!=frozen['policy_sha256']:raise ValueError('Existing run policy mismatch')
        else:m=replay(source,video,out,policy,embed)
        baseline=read(source/'identity/identity_timeline.json')['phone_timeline']
        m['old_authorized_sampled_frames']=sum(r.get('state') in {'VISIBLE','MATCHED','IDENTITY_CONFIRMED'} for r in baseline)
        old=read(source/'identity/target_binding.json');old=old.get('bound_target')
        new=read(out/'identity.json');first=new['aliases'][0] if new['aliases'] else None
        m['initial_track_matches_baseline']=bool(old and first and first['candidate_id']==f'track:{old["source_track_id"]}')
        m['old_initial_frame']=old['frame_index'] if old else None
        m['new_initial_frame']=first['confirmation_frame'] if first else None
        m['old_confirmed_recovery']=read(source/'identity/reid_audit.json').get('confirmed_match')
        rows=read(out/'authorized_rows.json')
        # These are evaluation assertions only. They are never passed to the guard.
        if v=='test8':m['f804_authorized']=any(r['frame']==804 and r['identity_authorized'] for r in rows);m['forward_authorized_after804']=sum(r['frame']>804 and r['identity_authorized'] for r in rows)
        if v in {'val_5','val_9','val_10'}:
            start={'val_5':1284,'val_9':1194,'val_10':1140}[v]
            end={'val_5':999999,'val_9':999999,'val_10':1859}[v]
            m['known_wrong_interval_authorized']=sum(start<=r['frame']<=end and r['identity_authorized'] for r in rows)
            bad={'val_5':'track:77','val_9':'track:52','val_10':'track:49'}[v]
            m['known_wrong_alias_active']=any(a['candidate_id']==bad and a['status']=='CONFIRMED' for a in new['aliases'])
            m['known_wrong_core_entries']=sum(b['active'] and b['candidate_id']==bad for b in new['banks']['core'])
        results[v]=m;write(out/'metrics.json',m)
        print(kind,v,'binding',m['initial_binding'],'obs',m['authorized_observations'],'/',m['old_authorized_sampled_frames'],
            'recoveries',m['confirmed_recoveries'],'seconds',round(m['wall_seconds'],1),flush=True)
    name='identity_metrics.json' if kind=='development' else 'val_1_to_11_identity_metrics.json'
    write(OUT/kind/name,{'scope':kind,'policy_sha256':frozen['policy_sha256'],'videos':results,
        'totals':{'initial_binding':sum(m['initial_binding'] for m in results.values()),
            'initial_track_matches_baseline':sum(m['initial_track_matches_baseline'] for m in results.values()),
            'authorized_observations':sum(m['authorized_observations'] for m in results.values()),
            'old_authorized_sampled_frames':sum(m['old_authorized_sampled_frames'] for m in results.values()),
            'confirmed_recoveries':sum(m['confirmed_recoveries'] for m in results.values()),
            'unresolved_candidate_frames':sum(m['unresolved_candidate_frames'] for m in results.values()),
            'wall_seconds':sum(m['wall_seconds'] for m in results.values())}})
    if kind=='development':
        write(OUT/'development/development_freeze.json',{'created_unix':time.time(),'policy_sha256':frozen['policy_sha256'],
            'identity_source_hashes':identity_hashes(),'metrics_sha256':sha(OUT/kind/name),
            'test8_recovery_loss':not results['test8']['f804_authorized']})
    else:
        write(OUT/kind/'false_merge_comparison.json',{'old_known_permanent_false_merges':3,
            'new_known_permanent_false_merges':sum(results[v]['known_wrong_alias_active'] for v in ('val_5','val_9','val_10')),
            'new_known_wrong_authorized_frames':sum(results[v]['known_wrong_interval_authorized'] for v in ('val_5','val_9','val_10')),
            'scope':'POST-VALIDATION KNOWN REGRESSION SET; not a new held-out accuracy estimate'})
        write(OUT/kind/'bank_contamination_comparison.json',{'old_val9_wrong_forward_updates':12,
            'new_val9_wrong_core_entries':results['val_9']['known_wrong_core_entries'],
            'new_val9_confirmed_recoveries':results['val_9']['confirmed_recoveries']})

def identity_hashes():
    paths=list((ROOT/'src/memory_graph/identity').glob('*.py'))+[ROOT/'scripts/run_findmind.py']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['calibrate','development','known_validation_regression'])
    cmd=parser.parse_args().command
    calibration() if cmd=='calibrate' else run_set(cmd)
