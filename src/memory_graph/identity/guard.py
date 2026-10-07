"""Single authority, one-use scoped capabilities and final-state materialization.

Opaque in-process capability handles cannot be reconstructed from audit JSON.
This enforces application API boundaries, not isolation from malicious Python
code with arbitrary access to process memory/private attributes.
"""
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from .contracts import Observation, Policy, digest, cosine, iou

CAPS={'authorize_observation':'AUTHORIZE_OBSERVATION','bind_alias':'BIND_ALIAS',
      'restart_sam':'RESTART_TARGET_SAM','commit_bank':'COMMIT_BANK_ENTRY','revoke_alias':'REVOKE_ALIAS'}

class IdentityGuard:
    def __init__(self, policy=None):
        self.policy=policy or Policy()
        self._observations={};self._candidates=defaultdict(list);self._decisions=[]
        self._aliases=[];self._banks={'core':[],'quarantine':[],'negative':[]}
        self._ledger=[];self._epochs=[];self._authorizations=[];self._issued={}
        self._tickets=[];self._now=-1.;self._last=None;self._active_alias=None
        self._bound=False;self._rejections=0;self._bank_rejections=0

    def _epoch(self):return self._epochs[-1] if self._epochs else None
    def _new_epoch(self, obs, reason):
        e={'epoch_id':len(self._epochs)+1,'start_time':self._now,'start_frame':obs.frame,
           'start_observation_id':obs.observation_id,'start_reason':reason,'end_time':None,'end_reason':None}
        self._epochs.append(e)
    def _close(self,reason):
        e=self._epoch()
        if e and e['end_time'] is None:e.update(end_time=self._now,end_reason=reason)
        self._last=None

    def _issue(self,obs,decision,capabilities,alias_id=None,bank_kind=None,parents=(),reason=''):
        # The handle itself is the unforgeable identity. Audit serialization is not accepted.
        handle=object();aid=f'auth:{len(self._authorizations)+1}'
        entry={'authorization_id':aid,'entity_id':'phone_01','candidate_id':obs.candidate_id,
            'source_observation_ids':[obs.observation_id],'epoch_id':self._epoch()['epoch_id'],
            'decision':decision,'capabilities':list(capabilities),'evidence_hash':digest(obs.data()),
            'decision_time':self._now,'decision_frame':obs.frame,'provenance':obs.provenance,
            'alias_id':alias_id,'bank_kind':bank_kind,'parent_lineage':list(parents),'reason':reason}
        self._issued[handle]={'record':entry,'remaining':set(capabilities)}
        self._authorizations.append(entry)
        return handle

    def _check(self,operation,token,obs,bank_kind=None):
        try:item=self._issued.get(token)
        except TypeError:item=None
        cap=CAPS.get(operation)
        e=self._epoch()
        if (not item or cap not in item['remaining'] or item['record']['evidence_hash']!=digest(obs.data())
            or obs.observation_id not in item['record']['source_observation_ids']
            or item['record']['candidate_id']!=obs.candidate_id
            or not e or (e['end_time'] is not None and not (operation=='commit_bank' and bank_kind=='quarantine')) or item['record']['epoch_id']!=e['epoch_id']
            or (operation=='commit_bank' and bank_kind!=item['record']['bank_kind'])
            or (item['record']['alias_id'] and any(a['alias_id']==item['record']['alias_id'] and a['status']=='REVOKED' for a in self._aliases))):
            self._rejections+=1
            if operation=='commit_bank':self._bank_rejections+=1
            raise PermissionError('Invalid, consumed, revoked, stale, or incorrectly scoped identity capability')
        item['remaining'].remove(cap)
        return item['record']

    def write(self,operation,token,obs,bank_kind=None):
        """All mutation sinks require a live scoped capability; snapshots are copies."""
        r=self._check(operation,token,obs,bank_kind)
        if operation=='bind_alias':
            alias={'alias_id':r['alias_id'],'candidate_id':obs.candidate_id,'entity_id':'phone_01',
                'status':'CONFIRMED','authorization_id':r['authorization_id'],'epoch_id':r['epoch_id'],
                'confirmation_frame':obs.frame,'confirmation_time':self._now,'evidence_refs':r['source_observation_ids'],
                'revocation_reason':None,'revocation_frame':None}
            self._aliases.append(alias);self._active_alias=alias['alias_id']
        elif operation=='authorize_observation':
            self._ledger.append({'observation':obs.data(),'candidate_id':obs.candidate_id,
                'authorization_id':r['authorization_id'],'epoch_id':r['epoch_id'],'alias_id':r['alias_id'],
                'evidence_hash':r['evidence_hash'],'parent_lineage':r['parent_lineage'],'active':True})
        elif operation=='commit_bank':
            if not obs.vector:raise ValueError('Cannot commit missing appearance evidence')
            self._banks[bank_kind].append({'entry_id':f'bank:{sum(map(len,self._banks.values()))+1}',
                'bank_kind':bank_kind,'entity_id':'phone_01' if bank_kind!='negative' else None,
                'candidate_id':obs.candidate_id,'observation_id':obs.observation_id,'epoch_id':r['epoch_id'],
                'authorization_id':r['authorization_id'],'frame':obs.frame,'time':obs.time,'alias_id':r['alias_id'],
                'reason':r['reason'],'status':'ACTIVE','active':True,'parent_lineage':r['parent_lineage'],
                'parent_authorization_ids':[a['authorization_id'] for a in self._aliases if a['alias_id'] in r['parent_lineage']]+
                    [b['authorization_id'] for rows in self._banks.values() for b in rows if b['entry_id'] in r['parent_lineage']],
                'provenance':obs.provenance,'embedding':list(obs.vector)})
        elif operation=='revoke_alias':
            self._revoke(r['alias_id'],r['reason'],obs.frame,r['authorization_id'])
        elif operation=='restart_sam':
            return {'authorization_id':r['authorization_id'],'epoch_id':r['epoch_id'],
                    'alias_id':r['alias_id'],'observation':obs.data()}
        return deepcopy(r)

    def restart_tickets(self):return list(self._tickets)
    def restart_target_sam(self,token,observation_id,callback):
        obs=self._observations.get(observation_id)
        if obs is None:raise PermissionError('Unknown seed')
        context=self.write('restart_sam',token,obs)
        return callback(context)

    def _revoke(self,alias_id,reason,frame,authorization_id):
        invalid={alias_id}
        revoked_candidates={a['candidate_id'] for a in self._aliases if a['alias_id']==alias_id}
        for a in self._aliases:
            if a['alias_id']==alias_id:
                a.update(status='REVOKED',revocation_reason=reason,revocation_frame=frame,
                         revocation_authorization_id=authorization_id)
        # Fixed-point lineage closure includes bank entries derived from other entries.
        changed=True
        while changed:
            changed=False
            for rows in self._banks.values():
                for row in rows:
                    if row['active'] and (row['alias_id'] in invalid or invalid.intersection(row['parent_lineage'])
                        or row['bank_kind']=='quarantine' and row['candidate_id'] in revoked_candidates):
                        row.update(active=False,status='REVOKED');invalid.add(row['entry_id']);changed=True
        for row in self._ledger:
            if row['alias_id'] in invalid or invalid.intersection(row['parent_lineage']):row['active']=False
        self._close(reason)
        self._active_alias=None

    def _bank(self,obs,kind,alias,reason,parents=()):
        token=self._issue(obs,'BANK_ADMISSION',['COMMIT_BANK_ENTRY'],alias,kind,parents,reason)
        self.write('commit_bank',token,obs,kind)

    def _authorize(self,obs,decision,new_alias=False,initial=False):
        alias=f'alias:{len(self._aliases)+1}' if new_alias else self._active_alias
        capabilities=['AUTHORIZE_OBSERVATION']
        if new_alias:capabilities+=['BIND_ALIAS','RESTART_TARGET_SAM']
        token=self._issue(obs,decision,capabilities,alias,parents=(alias,))
        if new_alias:self.write('bind_alias',token,obs);self._tickets.append(token)
        self.write('authorize_observation',token,obs)
        self._last=obs
        if new_alias and not initial and obs.vector:
            parents=[alias]+[b['entry_id'] for b in self._banks['core'] if b['active']]
            self._bank(obs,'quarantine',alias,'recent confirmation; not permanent target evidence',parents)

    def _initial(self,current):
        p=self.policy;eligible=[]
        # Preserve the frozen selector's all-seen ambiguity semantics. A missing
        # competing mature track is not evidence that it ceased to be a candidate.
        for history in self._candidates.values():
            obs=history[-1]
            if not obs.phone or obs.source=='sam':continue
            rows=[x for x in self._candidates[obs.candidate_id] if x.phone]
            quality=sum(x.confidence for x in rows)/len(rows)
            if (len(rows)>=p.minimum_binding_observations and rows[-1].time-rows[0].time+1e-9>=p.minimum_binding_span
                and quality>=p.minimum_confidence):eligible.append((quality,obs,rows))
        eligible.sort(key=lambda x:(-x[0],x[1].candidate_id))
        if not eligible or len(eligible)>1 and eligible[0][0]-eligible[1][0]<p.binding_quality_margin:return
        _,obs,rows=eligible[0]
        if obs not in current:return  # No stale seed / backdated current authority.
        self._bound=True;self._new_epoch(obs,'INITIAL_TARGET_BINDING')
        self._authorize(obs,'CONFIRMED_MATCH',new_alias=True,initial=True)
        # Causal initial binding evidence only. No future/recovered bank appends to core.
        for r in rows[-p.minimum_binding_observations:]:
            if r.vector:self._bank(r,'core',self._active_alias,'initial causal binding evidence',(self._active_alias,))
        self._decisions.append({'frame':obs.frame,'candidate_id':obs.candidate_id,'decision':'CONFIRMED_MATCH',
                                'reason':'INITIAL_TARGET_BINDING','epoch_id':self._epoch()['epoch_id']})

    def _scores(self,obs):
        core=[b for b in self._banks['core'] if b['active']]
        scores=[cosine(obs.vector,b['embedding']) for b in core];scores=[s for s in scores if s is not None]
        negatives=[cosine(obs.vector,b['embedding']) for b in self._banks['negative'] if b['active']]
        negatives=[s for s in negatives if s is not None]
        return core,scores,max(negatives,default=None)

    def _candidate_decision(self,obs,current):
        p=self.policy;core,scores,negative=self._scores(obs);best=max(scores,default=None)
        # Only simultaneous spatially separate hypotheses establish distinct physical competitors.
        competing=[x for x in current if x.phone and x.candidate_id!=obs.candidate_id and iou(x.bbox,obs.bbox)<p.coexistence_iou]
        competitor_scores=[max(self._scores(x)[1],default=-1.) for x in competing if x.vector]
        second=max(competitor_scores,default=None);margin=best-second if best is not None and second is not None else None
        recent=[x for x in self._candidates[obs.candidate_id] if x.time>=obs.time-p.persistence_span-1e-8]
        persistent=(len(recent)>=p.persistence_observations and recent[-1].time-recent[0].time+1e-8>=p.persistence_span
            and all(len(self._scores(x)[1])>=p.minimum_prototypes and min(self._scores(x)[1])>=p.admission_similarity for x in recent))
        coexist=any(x.phone and x.candidate_id!=obs.candidate_id and iou(x.bbox,obs.bbox)<p.coexistence_iou and
            any(a['candidate_id']==x.candidate_id and a['status']=='CONFIRMED' for a in self._aliases) for x in current)
        gates={'semantic_compatible':obs.phone,'trusted_core_appearance':best is not None and best>=p.admission_similarity,
            'multiple_prototypes_consistent':len(scores)>=p.minimum_prototypes and min(scores)>=p.admission_similarity,
            'multi_time_persistence':persistent,'physical_competitor_available':bool(competitor_scores),
            'physical_competitor_margin':margin is not None and margin>=p.physical_competitor_margin,
            'no_coexistence_contradiction':not coexist,'no_negative_match':negative is None or best is not None and negative<max(p.admission_similarity,best),
            'core_provenance_valid':len(core)>=p.minimum_prototypes and all(b['authorization_id'] and b['parent_lineage'] for b in core),
            'epoch_broken':bool(self._epoch() and self._epoch()['end_time'] is not None),
            'calibrated_confirmation':p.automatic_confirmation_enabled}
        if not gates['semantic_compatible'] or not gates['no_negative_match'] or coexist:
            decision='REJECTED'
        elif best is None:decision='AMBIGUOUS'
        elif margin is not None and margin<p.physical_competitor_margin:decision='AMBIGUOUS'
        elif not gates['trusted_core_appearance']:decision='REJECTED'
        elif all(gates.values()):decision='CONFIRMED_MATCH'
        else:decision='PROVISIONAL'
        self._decisions.append({'frame':obs.frame,'time':obs.time,'candidate_id':obs.candidate_id,
            'decision':decision,'gates':gates,'prototype_similarities':scores,'best_similarity':best,
            'second_physical_candidate_similarity':second,'physical_margin':margin,'negative_similarity':negative,
            'competitor_ids':[x.candidate_id for x in competing],'observation_id':obs.observation_id,
            'calibration_id':p.calibration_id,'epoch_id':self._epoch()['epoch_id'] if self._epoch() else None})
        if decision=='CONFIRMED_MATCH':
            self._new_epoch(obs,'MULTI_EVIDENCE_REIDENTIFICATION');self._authorize(obs,decision,new_alias=True)
        elif decision=='PROVISIONAL' and obs.vector:
            if not any(b['candidate_id']==obs.candidate_id and b['active'] for b in self._banks['quarantine']):
                parents=[b['entry_id'] for b in core]
                self._bank(obs,'quarantine',None,'PROVISIONAL; cannot serve as target evidence',parents)
        return decision

    def process(self,timestamp,observations):
        if timestamp<=self._now:raise ValueError('Frames must be strictly causal and unique')
        observations=list(observations)
        ids=[x.observation_id for x in observations]
        if len(set(ids))!=len(ids) or any(x.observation_id in self._observations or abs(x.time-timestamp)>1e-6 for x in observations):
            raise ValueError('Duplicate, stale, or mismatched observation')
        self._now=timestamp
        for x in observations:self._observations[x.observation_id]=x;self._candidates[x.candidate_id].append(x)
        if not self._bound:self._initial(observations);return
        p=self.policy
        if self._last and timestamp-self._last.time>p.gap_seconds+.001:self._close('OBSERVATION_GAP')
        if self._last and any(x.scene_break for x in observations):self._close('SCENE_BREAK')
        if self._last:
            prev=self._last
            matches=[x for x in observations if x.phone and x.source!='sam' and not x.drift and
                iou(x.bbox,prev.bbox)>=p.continuity_iou and
                (x.candidate_id==prev.candidate_id or x.sam_overlap>=p.support_iou)]
            claims=[x for x in observations if x.phone and any(a['candidate_id']==x.candidate_id and a['status']=='CONFIRMED' for a in self._aliases)]
            contradiction=next(((a,b) for a in claims for b in claims if a.candidate_id!=b.candidate_id and iou(a.bbox,b.bbox)<p.coexistence_iou),None)
            if contradiction:
                # Revoke the latest claim, retaining initial core to permit later recovery.
                seed=next(x for x in claims if any(a['alias_id']==self._active_alias and a['candidate_id']==x.candidate_id for a in self._aliases))
                tok=self._issue(seed,'REVOKED',['REVOKE_ALIAS'],self._active_alias,reason='COEXISTING_TARGET_CLAIMS')
                self.write('revoke_alias',tok,seed)
            elif len(matches)>1:self._close('AMBIGUOUS_COMPETITORS')
            elif len(matches)==1:
                x=matches[0];core,scores,negative=self._scores(x)
                if negative is not None and negative>=max(p.admission_similarity,max(scores,default=-1.)):
                    tok=self._issue(x,'REVOKED',['REVOKE_ALIAS'],self._active_alias,reason='KNOWN_DISTRACTOR_MATCH');self.write('revoke_alias',tok,x)
                elif len(scores)>=p.minimum_prototypes and max(scores)<p.admission_similarity:
                    if self._active_alias!=self._aliases[0]['alias_id']:
                        tok=self._issue(x,'REVOKED',['REVOKE_ALIAS'],self._active_alias,reason='CORE_APPEARANCE_CONTRADICTION');self.write('revoke_alias',tok,x)
                    else:self._close('CORE_APPEARANCE_CONTRADICTION')
                else:
                    self._authorize(x,'CONTINUITY_AUTHORIZED')
                    for other in observations:
                        if other.phone and other.vector and iou(other.bbox,x.bbox)<p.coexistence_iou:
                            if not any(b['candidate_id']==other.candidate_id and b['active'] for b in self._banks['negative']):
                                self._bank(other,'negative',self._active_alias,'coexisting spatially separate phone',(self._active_alias,))
                    return
            elif any(x.drift for x in observations):self._close('SAM_DRIFT')
            elif any(x.candidate_id==prev.candidate_id for x in observations):self._close('UNSUPPORTED_RELOCATION')
        for x in observations:self._candidate_decision(x,observations)

    def final_ledger(self):
        valid={a['alias_id'] for a in self._aliases if a['status']=='CONFIRMED'}
        return deepcopy([r for r in self._ledger if r['active'] and r['alias_id'] in valid])

    def snapshot(self):
        return deepcopy({'policy':asdict(self.policy),'epochs':self._epochs,'aliases':self._aliases,
            'banks':self._banks,'ledger':self._ledger,'final_ledger':self.final_ledger(),
            'decisions':self._decisions,'authorizations':self._authorizations,
            'candidate_registry':{k:{'observation_ids':[x.observation_id for x in v],
                'first_time':v[0].time,'last_time':v[-1].time,'status':next((d['decision'] for d in reversed(self._decisions) if d['candidate_id']==k),'UNVERIFIED')} for k,v in self._candidates.items()},
            'invalid_write_attempts':self._rejections,'rejected_bank_updates':self._bank_rejections})
