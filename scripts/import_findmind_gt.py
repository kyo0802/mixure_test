"""Collect independent human submissions; explicit adjudication is the only GT gate."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from findmind_gt_contract import (TOOL, ATTESTATIONS, STATES, VISIBILITY, canonical, digest,
    exhaustiveness, file_sha, load_json, submission_fingerprint, validate_bundle)

def write(path, value):
    with Path(path).open('x',encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

def table(path, fields, rows):
    with Path(path).open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in rows:
            # Spreadsheet safety; originals are preserved unchanged in JSON.
            clean={k:(' '+str(v) if str(v).startswith(('=','+','-','@')) else v) for k,v in row.items()}
            writer.writerow(clean)

def collect(input_dir, output_dir, manifest, gap=1.0):
    output_dir=Path(output_dir)
    if output_dir.exists(): raise ValueError('Output directory already exists; choose a new collection path')
    files=sorted(Path(input_dir).glob('*.json'))
    if not files: raise ValueError('No JSON submissions found')
    output_dir.mkdir(parents=True);(output_dir/'submissions').mkdir()
    accepted=[];duplicates=[];rejected=[];fingerprints={};sessions=defaultdict(list);by_video={v['video_id']:{'events':[],'states':[],'coverage':[]} for v in manifest['videos']}
    for source in files:
        try:
            if source.stat().st_size>20*1024*1024: raise ValueError('Submission over 20 MB')
            bundle=load_json(source);errors=validate_bundle(bundle,manifest)
            if errors: raise ValueError('; '.join(errors[:20]))
            content_sha=file_sha(source);fingerprint=submission_fingerprint(bundle)
            preserved=output_dir/'submissions'/f'{content_sha}.json'
            if not preserved.exists():preserved.write_bytes(source.read_bytes())
            if fingerprint in fingerprints:
                duplicates.append({'filename':source.name,'duplicate_of':fingerprints[fingerprint],'sha256':content_sha});continue
            fingerprints[fingerprint]=content_sha
            prov={'submission_sha256':content_sha,'filename':source.name,'reviewer_id':bundle['reviewer_id'],'session_id':bundle['session_id'],'updated_at':bundle['updated_at'],'semantic_fingerprint':fingerprint}
            accepted.append(prov);sessions[(bundle['reviewer_id'],bundle['session_id'])].append(content_sha)
            for v in bundle['videos']:
                base={'submission_sha256':content_sha,'reviewer_id':bundle['reviewer_id'],'session_id':bundle['session_id'],'video_id':v['video_id'],'source_sha256':v['source_sha256']}
                by_video[v['video_id']]['coverage'].append({**base,'ref':content_sha+':'+v['video_id']+':coverage','record':v})
                for kind,id_key in [('events','event_id'),('states','state_id')]:
                    for item in v[kind]:by_video[v['video_id']][kind].append({**base,'ref':content_sha+':'+v['video_id']+':'+item[id_key],'record':item})
        except (ValueError,KeyError,TypeError,OverflowError) as e:
            rejected.append({'filename':source.name,'error':str(e)})
    revisions=[{'reviewer_id':k[0],'session_id':k[1],'submissions':v,'status':'SESSION_REVISION_CONFLICT_NO_AUTO_SELECTION'} for k,v in sessions.items() if len(v)>1]
    candidates=[];event_decisions=[];state_decisions=[];coverage_decisions=[]
    for vid,data in by_video.items():
        es=data['events']
        for i,a in enumerate(es):
            for b in es[i+1:]:
                if a['submission_sha256']==b['submission_sha256']:continue
                x,y=a['record'],b['record'];distance=max(y['start_s']-x['end_s'],x['start_s']-y['end_s'],0)
                if distance>gap:continue
                flags=[]
                if x['type']!=y['type']:flags.append('TYPE_DIFFERENCE')
                if x['object_category'].casefold()!=y['object_category'].casefold():flags.append('CATEGORY_DIFFERENCE')
                if x['local_instance_id']!=y['local_instance_id']:flags.append('LOCAL_ID_NAMES_DIFFER_NOT_PHYSICAL_ID_PROOF')
                if [x['start_s'],x['end_s']]!=[y['start_s'],y['end_s']]:flags.append('TIMING_DIFFERENCE')
                if [x['before_state'],x['after_state']]!=[y['before_state'],y['after_state']]:flags.append('STATE_DIFFERENCE')
                if x['evidence_certainty']!=y['evidence_certainty']:flags.append('CERTAINTY_DIFFERENCE')
                if a['reviewer_id']==b['reviewer_id']:flags.append('SAME_REVIEWER_NOT_INDEPENDENT')
                candidates.append({'video_id':vid,'a_ref':a['ref'],'b_ref':b['ref'],'interval_gap_s':distance,'same_type':x['type']==y['type'],'same_category':x['object_category'].casefold()==y['object_category'].casefold(),'flags':';'.join(flags) or 'LABELS_AGREE_IDENTITY_UNADJUDICATED'})
        for e in es:
            x=e['record'];event_decisions.append({'decision_id':digest(e['ref'])[:20],'source_refs':[e['ref']], 'decision':'UNRESOLVED','final_event_id':'','video_id':vid,'type':x['type'],'object_category':x['object_category'],'reviewed_object_id':'','time_interval':[x['start_s'],x['end_s']], 'before_state':x['before_state'],'after_state':x['after_state'],'before_evidence_times_s':x['before_evidence_times_s'],'after_evidence_times_s':x['after_evidence_times_s'],'evidence_supported':False,'target_identity_confirmed':False,'adjudicator_id':'','notes':''})
        for e in data['states']:
            x=e['record'];state_decisions.append({'decision_id':digest(e['ref'])[:20],'source_refs':[e['ref']],'decision':'UNRESOLVED','final_state_id':'','video_id':vid,'reviewed_object_id':'','source_time_s':x['source_time_s'],'physical_state':x['physical_state'],'visibility':x['visibility'],'evidence_certainty':x['evidence_certainty'],'evidence_supported':False,'adjudicator_id':'','notes':''})
        # Sources are listed for inspection, never treated as owner approval.
        coverage_decisions.append({'video_id':vid,'decision':'UNRESOLVED','source_refs':[e['ref'] for e in data['coverage']], 'start_s':0,'end_s':next(m['source_duration_s'] for m in manifest['videos'] if m['video_id']==vid),'attestations':{k:False for k in ATTESTATIONS},'adjudicator_id':'','notes':''})
    adjudication={'schema_version':'findmind_gt_adjudication_1.0','dataset_manifest_sha256':manifest['dataset_manifest_sha256'],'events':event_decisions,'states':state_decisions,'coverage':coverage_decisions,'instructions':'Edit a COPY. ACCEPT keeps source labels; CORRECT records explicit owner corrections. Repeated final_event_id requires identical final event fields. REJECT needs a reason. UNRESOLVED is excluded. No majority voting.'}
    write(output_dir/'collection.json',{'schema_version':'findmind_gt_collection_1.0','dataset_manifest_sha256':manifest['dataset_manifest_sha256'],'submissions':accepted,'duplicates':duplicates,'rejected':rejected,'session_revision_conflicts':revisions,'candidate_gap_s':gap,'by_video':by_video,'authoritative_gt_created':False})
    write(output_dir/'adjudication.json',adjudication)
    table(output_dir/'event_correspondence.csv',['video_id','a_ref','b_ref','interval_gap_s','same_type','same_category','flags'],candidates)
    state_pairs=[]
    for vid,data in by_video.items():
        for i,a in enumerate(data['states']):
            for b in data['states'][i+1:]:
                x,y=a['record'],b['record']
                if a['submission_sha256']==b['submission_sha256'] or abs(x['source_time_s']-y['source_time_s'])>gap:continue
                state_pairs.append({'video_id':vid,'a_ref':a['ref'],'b_ref':b['ref'],'time_difference_s':abs(x['source_time_s']-y['source_time_s']),'flags':';'.join(k for k,f in [('STATE_DIFFERENCE',x['physical_state']!=y['physical_state']),('VISIBILITY_DIFFERENCE',x['visibility']!=y['visibility']),('CATEGORY_DIFFERENCE',x['object_category'].casefold()!=y['object_category'].casefold()),('LOCAL_ID_NAMES_DIFFER',x['local_instance_id']!=y['local_instance_id'])] if f) or 'LABELS_AGREE_UNADJUDICATED'})
    table(output_dir/'state_comparison.csv',['video_id','a_ref','b_ref','time_difference_s','flags'],state_pairs)
    matched={v for pair in candidates for v in (pair['a_ref'],pair['b_ref'])}
    table(output_dir/'event_inventory.csv',['ref','video_id','reviewer_id','session_id','type','category','start_s','end_s','candidate_correspondence'],[{'ref':e['ref'],'video_id':vid,'reviewer_id':e['reviewer_id'],'session_id':e['session_id'],'type':e['record']['type'],'category':e['record']['object_category'],'start_s':e['record']['start_s'],'end_s':e['record']['end_s'],'candidate_correspondence':e['ref'] in matched} for vid,data in by_video.items() for e in data['events']])
    summary={'valid_unique_submissions':len(accepted),'duplicate_submissions':len(duplicates),'rejected_submissions':len(rejected),'session_revision_conflicts':len(revisions),'event_records':len(event_decisions),'state_records':len(state_decisions),'possible_correspondences':len(candidates),'correspondences_with_differences':sum(x['flags']!='LABELS_AGREE_IDENTITY_UNADJUDICATED' for x in candidates),'authoritative_gt_records':0}
    write(output_dir/'import_summary.json',summary)
    (output_dir/'README.md').write_text('# Human GT collection\n\nOriginal submitted bytes are in submissions/. collection.json preserves labels and provenance. CSV correspondences are heuristic candidates, never automatic physical identity or event merges.\n\nCopy adjudication.json, resolve event/state/coverage rows explicitly, then use --finalize. Select or reject competing session revisions explicitly; timestamps do not automatically pick a winner. No formal metrics are calculated here.\n\n'+json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    return summary

def finalize(collection_dir, adjudication_file, output_file, manifest):
    base=Path(collection_dir);collection=load_json(base/'collection.json');adj=load_json(adjudication_file)
    if adj.get('schema_version')!='findmind_gt_adjudication_1.0' or adj.get('dataset_manifest_sha256')!=manifest['dataset_manifest_sha256'] or collection['dataset_manifest_sha256']!=manifest['dataset_manifest_sha256']:raise ValueError('Adjudication dataset/schema mismatch')
    expected_refs={}
    for s in collection['submissions']:
        p=base/'submissions'/f"{s['submission_sha256']}.json"
        if file_sha(p)!=s['submission_sha256']:raise ValueError('Original submission changed')
        original=load_json(p);errors=validate_bundle(original,manifest)
        if errors:raise ValueError(str(errors[:10]))
        if original['reviewer_id']!=s['reviewer_id'] or original['session_id']!=s['session_id']:raise ValueError('Reviewer/session provenance changed')
        for v in original['videos']:
            provenance={'submission_sha256':s['submission_sha256'],'video_id':v['video_id'],'reviewer_id':original['reviewer_id'],'session_id':original['session_id'],'source_sha256':v['source_sha256']}
            expected_refs[s['submission_sha256']+':'+v['video_id']+':coverage']={**provenance,'record':v}
            for kind,key in [('events','event_id'),('states','state_id')]:
                for x in v[kind]:expected_refs[s['submission_sha256']+':'+v['video_id']+':'+x[key]]={**provenance,'record':x}
    refs={e['ref']:e for v in collection['by_video'].values() for kind in ('events','states','coverage') for e in v[kind]}
    if set(refs)!=set(expected_refs) or any(any(refs[k].get(field)!=value for field,value in v.items()) for k,v in expected_refs.items()):raise ValueError('Collection labels/provenance differ from original submissions')
    durations={v['video_id']:v['source_duration_s'] for v in manifest['videos']};hashes={v['video_id']:v['source_sha256'] for v in manifest['videos']}
    errors=[];decided=set();events={};states={};limited=[];coverage=[];used_refs=set();decision_ids=set()
    def fail(text):errors.append(text)
    def finite(t):return isinstance(t,(int,float)) and not isinstance(t,bool) and -float('inf')<t<float('inf')
    def valid_times(a,vid):return isinstance(a,list) and all(finite(t) and 0<=t<=durations[vid]+1e-8 for t in a)
    for kind in ('events','states'):
        for row in adj.get(kind,[]):
            if not isinstance(row.get('decision_id'),str) or not row['decision_id'].strip():fail('Missing decision ID');continue
            if row.get('decision_id') in decision_ids:fail('Duplicate decision ID')
            decision_ids.add(row.get('decision_id'))
            decision=row.get('decision');vid=row.get('video_id');source_refs=row.get('source_refs',[])
            if decision not in ('UNRESOLVED','ACCEPT','CORRECT','REJECT'):fail('Unknown adjudication decision');continue
            if not isinstance(source_refs,list) or not source_refs or len(source_refs)!=len(set(source_refs)) or any(r not in refs or refs[r]['video_id']!=vid or r not in {e['ref'] for e in collection['by_video'].get(vid,{}).get(kind,[])} for r in source_refs):fail('Unknown/duplicate/wrong-kind/source-video reference');continue
            if decision=='UNRESOLVED':continue
            if not row.get('adjudicator_id','').strip():fail('Missing human adjudicator ID');continue
            if any(r in used_refs for r in source_refs):fail('Source label adjudicated more than once');continue
            used_refs.update(source_refs)
            if decision=='REJECT':
                if not row.get('notes','').strip():fail('REJECT needs a reason')
                decided.update(source_refs);continue
            if not row.get('evidence_supported') is True:fail('Positive adjudication requires explicit physical support');continue
            object_id=row.get('reviewed_object_id','').strip()
            if not object_id or object_id.upper()=='UNKNOWN':fail('Missing explicitly adjudicated object identity');continue
            if kind=='events':
                interval=row.get('time_interval');bf=row.get('before_evidence_times_s');af=row.get('after_evidence_times_s');etype=row.get('type')
                if etype not in ('PICKUP','PLACEMENT'):fail('Non-event observation cannot become a physical positive without CORRECT and supported event fields');continue
                if not valid_times(interval,vid) or len(interval)!=2 or interval[0]>interval[1]:fail('Invalid event interval');continue
                pair=('ON_SURFACE','HELD_BY_PERSON') if etype=='PICKUP' else ('HELD_BY_PERSON','ON_SURFACE')
                if not row.get('target_identity_confirmed') is True or (row.get('before_state'),row.get('after_state'))!=pair or not valid_times(bf,vid) or not bf or not valid_times(af,vid) or not af or max(bf)>min(af):fail('Event needs identity and supported chronological before/after states');continue
                if decision=='ACCEPT' and any(refs[r]['record']['type']!=etype or [refs[r]['record']['start_s'],refs[r]['record']['end_s']]!=interval or refs[r]['record']['before_state']!=pair[0] or refs[r]['record']['after_state']!=pair[1] or refs[r]['record']['before_evidence_times_s']!=bf or refs[r]['record']['after_evidence_times_s']!=af for r in source_refs):fail('ACCEPT changes a label; use CORRECT');continue
                if decision=='ACCEPT' and any(refs[r]['record']['evidence_certainty']!='CONFIRMED' or refs[r]['record']['target_identity_certainty']!='CERTAIN' or refs[r]['record']['local_instance_id'].strip().upper()=='UNKNOWN' or refs[r]['record']['before_visibility'] in ('NOT_VISIBLE','UNCERTAIN') or refs[r]['record']['after_visibility'] in ('NOT_VISIBLE','UNCERTAIN') for r in source_refs):fail('Resolving an uncertain source label requires CORRECT');continue
                eid=row.get('final_event_id','').strip()
                if not eid:fail('Missing final_event_id');continue
                if not row.get('object_category','').strip():fail('Missing adjudicated object category');continue
                if decision=='ACCEPT' and any(refs[r]['record']['object_category']!=row['object_category'] for r in source_refs):fail('ACCEPT changes object category; use CORRECT');continue
                item={'event_id':eid,'video_id':vid,'video_sha256':hashes[vid],'type':etype,'object_category':row['object_category'],'reviewed_object_id':object_id,'time_interval':interval,'before_state':pair[0],'after_state':pair[1],'before_evidence_times_s':bf,'after_evidence_times_s':af,'review_status':'HUMAN_REVIEWED','adjudicator_id':row['adjudicator_id'],'adjudicator_ids':[row['adjudicator_id']],'decision_ids':[row['decision_id']],'source_refs':list(source_refs),'notes':row.get('notes','')}
                key=(vid,eid)
                if key in events:
                    old=events[key];compare=['type','object_category','reviewed_object_id','time_interval','before_state','after_state','before_evidence_times_s','after_evidence_times_s']
                    if any(old[k]!=item[k] for k in compare):fail('Conflicting definitions of same final_event_id');continue
                    old['source_refs'].extend(source_refs)
                    old['adjudicator_ids']=sorted(set(old['adjudicator_ids']+item['adjudicator_ids']));old['decision_ids'].extend(item['decision_ids'])
                else:events[key]=item
            else:
                t=row.get('source_time_s');state=row.get('physical_state');vis=row.get('visibility')
                if not valid_times([t],vid) or state not in STATES or vis not in VISIBILITY or row.get('evidence_certainty') not in ('CONFIRMED','UNCERTAIN','INSUFFICIENT'):fail('Invalid final state');continue
                if state in ('ON_SURFACE','HELD_BY_PERSON') and vis in ('NOT_VISIBLE','UNCERTAIN') and row['evidence_certainty']=='CONFIRMED':fail('Invisible final state lacks confirmed support');continue
                if decision=='ACCEPT' and any(any(refs[r]['record'][k]!=row[k] for k in ('source_time_s','physical_state','visibility','evidence_certainty')) for r in source_refs):fail('ACCEPT changes a state; use CORRECT');continue
                sid=row.get('final_state_id','').strip()
                if not sid:fail('Missing final_state_id');continue
                item={'state_id':sid,'video_id':vid,'video_sha256':hashes[vid],'reviewed_object_id':object_id,'source_time_s':t,'source_frame_index':None,'state':state,'visibility':vis,'evidence_certainty':row['evidence_certainty'],'review_status':'HUMAN_REVIEWED','adjudicator_ids':[row['adjudicator_id']],'decision_ids':[row['decision_id']],'source_refs':list(source_refs),'notes':row.get('notes','')}
                key=(vid,sid)
                if key in states:
                    old=states[key]
                    if any(old[k]!=item[k] for k in ('reviewed_object_id','source_time_s','state','visibility','evidence_certainty')):fail('Conflicting definitions of same final_state_id');continue
                    old['source_refs'].extend(source_refs);old['decision_ids'].extend(item['decision_ids']);old['adjudicator_ids']=sorted(set(old['adjudicator_ids']+item['adjudicator_ids']))
                else:states[key]=item
            decided.update(source_refs)
    seen_coverage=set()
    for row in adj.get('coverage',[]):
        vid=row.get('video_id')
        if vid not in durations or vid in seen_coverage:fail('Unknown/duplicate coverage video');continue
        seen_coverage.add(vid)
        if row.get('decision') in ('UNRESOLVED','RETAIN_LIMITED'):continue
        if row.get('decision')!='ACCEPT_EXHAUSTIVE':fail('Unknown coverage decision');continue
        source_refs=row.get('source_refs',[])
        if not source_refs or any(r not in refs or r not in {e['ref'] for e in collection['by_video'][vid]['coverage']} for r in source_refs):fail('Coverage source refs invalid');continue
        if not row.get('adjudicator_id','').strip() or not all(row.get('attestations',{}).get(k) is True for k in ATTESTATIONS):fail('Coverage requires explicit owner attestations');continue
        if row.get('start_s')!=0 or row.get('end_s')!=durations[vid]:fail('Full-video eligibility requires complete native interval');continue
        if not any(exhaustiveness(refs[r]['record'])=='EXHAUSTIVE_ATTESTED' for r in source_refs):fail('No human submission explicitly attested eligible coverage');continue
        missing={e['ref'] for e in collection['by_video'][vid]['events']}-decided
        if missing:fail('Unresolved event/observation labels block exhaustive final GT');continue
        coverage.append({'video_id':vid,'video_sha256':hashes[vid],'start_s':0,'end_s':durations[vid],'review_status':'HUMAN_REVIEWED','reviewer_id':row['adjudicator_id'],'coverage':'EXHAUSTIVE_ATTESTED','entire_interval_reviewed':True,'all_pickup_placement_annotated':True,'no_unobservable_gap':True,'target_association_resolved':True,'ontology':'PICKUP_PLACEMENT_ONLY','excluded':False,'source_refs':source_refs,'notes':row.get('notes','')})
    # Every original label must still appear in the editable decision inventory.
    for kind in ('events','states'):
        original={e['ref'] for v in collection['by_video'].values() for e in v[kind]}
        represented={r for row in adj.get(kind,[]) for r in row.get('source_refs',[])}
        if represented!=original:fail('Adjudication removed or invented original '+kind+' references')
    if errors:raise ValueError('\n'.join(errors))
    eligible={c['video_id'] for c in coverage};truth=[e for e in events.values() if e['video_id'] in eligible];limited=[e for e in events.values() if e['video_id'] not in eligible]
    result={'schema_version':'findmind_evaluator_human_gt_1.0','dataset_manifest_sha256':manifest['dataset_manifest_sha256'],'collection_sha256':file_sha(base/'collection.json'),'adjudication_sha256':file_sha(adjudication_file),'adjudication_snapshot':adj,'source_submissions':collection['submissions'],'truth':truth,'coverage':coverage,'supported_events_non_exhaustive':limited,'states':list(states.values()),'unresolved_event_decisions':sum(x.get('decision')=='UNRESOLVED' for x in adj['events']),'unresolved_state_decisions':sum(x.get('decision')=='UNRESOLVED' for x in adj['states']),'formal_metrics_calculated':False,'model_proposal_identity_mapping_still_requires_human_review':True}
    write(output_file,result);return {'authoritative_events':len(truth),'non_exhaustive_supported_events':len(limited),'eligible_coverage_videos':len(coverage),'explicitly_adjudicated_states':len(states)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=TOOL/'manifest.json')
    parser.add_argument('--input-dir',type=Path);parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--candidate-gap',type=float,default=1.0)
    parser.add_argument('--finalize',type=Path,metavar='COLLECTION_DIR');parser.add_argument('--adjudication',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();manifest=load_json(args.manifest)
    if digest({k:v for k,v in manifest.items() if k!='dataset_manifest_sha256'})!=manifest['dataset_manifest_sha256']:raise ValueError('Manifest hash invalid')
    if args.finalize:
        if not args.adjudication or not args.output:parser.error('--finalize requires --adjudication and --output')
        result=finalize(args.finalize,args.adjudication,args.output,manifest)
    else:
        if not args.input_dir or not args.output_dir:parser.error('--input-dir and --output-dir required')
        if not 0<=args.candidate_gap<=10:parser.error('candidate-gap must be 0..10 seconds; descriptive candidate search only')
        result=collect(args.input_dir,args.output_dir,manifest,args.candidate_gap)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result.get('rejected_submissions',0):raise SystemExit(2)

if __name__=='__main__':main()
