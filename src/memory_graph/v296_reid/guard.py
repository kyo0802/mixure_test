"""Policy extensions only; original capability sinks and revocation are unchanged."""
from memory_graph.identity.guard import IdentityGuard
from memory_graph.identity.contracts import cosine,iou
from .evidence import TemporalAccumulator
from .integrity import provenance,clean

class V296IdentityGuard(IdentityGuard):
    def __init__(self,policy,recovery,metadata,v2,geometry,photometric):
        super().__init__(policy);self.recovery=recovery;self.metadata=metadata;self.v2=v2;self.geometry=geometry;self.photometric=photometric
        self.accumulator=TemporalAccumulator(recovery);self.backfill_events=[];self.confirmation_audit=[];self.bank_events=[]
    def process(self,timestamp,observations):
        if timestamp<=self._now:raise ValueError('Frames must remain strictly causal')
        obs=list(observations)
        # A physical candidate-epoch break cannot be traversed by inherited SAM overlap continuity.
        if self._last:
            previous=self.metadata[self._last.observation_id]
            changes=[self.metadata[o.observation_id] for o in obs if self.metadata[o.observation_id].get('local_track_id')==previous.get('local_track_id') and o.candidate_id!=self._last.candidate_id]
            if not any(o.candidate_id==self._last.candidate_id for o in obs):
                changes += [self.metadata[o.observation_id] for o in obs if o.candidate_id!=self._last.candidate_id and o.sam_overlap>=self.policy.support_iou and iou(o.bbox,self._last.bbox)>=self.policy.continuity_iou]
            if changes:
                previous_now=self._now;self._now=timestamp;self._close('CANDIDATE_EPOCH_BOUNDARY');self._now=previous_now
        eligible=[o for o in obs if not self.metadata[o.observation_id].get('epoch_unresolved')]
        # Provisional change-point frames remain unregistered and cannot be backfilled.
        return super().process(timestamp,eligible)
    def _sources(self,kind):
        authorization_times={a['authorization_id']:a['decision_time'] for a in self._authorizations}
        return [{**self.metadata[b['observation_id']],**b,'created_time':authorization_times[b['authorization_id']]} for b in self._banks[kind]]
    def _candidate_decision(self,obs,current):
        histories=[self.metadata[o.observation_id] for o in self._candidates[obs.candidate_id]]
        histories[-1]['candidate_alias_ids']=[a['alias_id'] for a in self._aliases if a['candidate_id']==obs.candidate_id]
        current_rows=[]
        for o in current:
            r=self.metadata[o.observation_id];r['authorized_target']=bool(self._last and self._last.candidate_id==o.candidate_id)
            current_rows.append(r)
        result=self.accumulator.evaluate(histories,self._sources('core'),self._sources('negative'),current_rows,
            bool(self._epoch() and self._epoch()['end_time'] is not None),self.v2,self.geometry,self.photometric)
        record={**result,'decision':result['stage'],'observation_id':obs.observation_id,'epoch_id':self._epoch()['epoch_id'] if self._epoch() else None,
                'reason':'V296_CURRENT_INDEPENDENT_CLEAN_DUAL_ROUTE'}
        self._decisions.append(record)
        if result['stage']=='CONFIRMED_MATCH':
            self._new_epoch(obs,'MULTI_EVIDENCE_REIDENTIFICATION');self._authorize(obs,'CONFIRMED_MATCH',new_alias=True)
            backfill=self._backfill(obs,result)
            record['identity_epoch_id']=self._epoch()['epoch_id'];record['authorization_capability']=self._ledger[-len(backfill['backfilled_observation_ids'])-1]['authorization_id'] if backfill['backfilled_observation_ids'] else self._ledger[-1]['authorization_id']
            record['alias_id']=self._active_alias;record['backfill']=backfill;self.confirmation_audit.append(record)
        elif result['stage']=='PROVISIONAL' and self._epoch():
            if not any(b['active'] and b['candidate_id']==obs.candidate_id for b in self._banks['quarantine']):
                self._bank(obs,'quarantine',None,'PROVISIONAL; no target Core evidence',[b['entry_id'] for b in self._banks['core'] if b['active']])
        return result['stage']
    def _backfill(self,current,result):
        support=dict(zip(result['observation_ids'],result['DINOv3']['per_frame']))
        v2support={oid:sum(sorted(scores,reverse=True)[:2])/min(2,len(scores)) for oid,scores in zip(result['observation_ids'],result['DINOv2_matrix']) if scores}
        ids=set(result['observation_ids']);rows=[]
        for obs in self._candidates[current.candidate_id]:
            r=self.metadata[obs.observation_id]
            if obs.observation_id==current.observation_id or obs.observation_id not in ids:continue
            if obs.candidate_id!=current.candidate_id or obs.time<r['candidate_epoch_start'] or obs.scene_break or obs.drift or not clean(r):continue
            threshold=self.recovery.a_lower if result['route']=='A' else self.recovery.g_lower
            if support.get(obs.observation_id,-1.)<threshold or v2support.get(obs.observation_id,-1.)<self.recovery.v2_support:continue
            if self.photometric(r,self._sources('core'))['state']=='STRONG_CONTRADICTION':continue
            if any(x['observation']['observation_id']==obs.observation_id and x['active'] for x in self._ledger):continue
            # Same epoch's vetted temporal evidence only; scoped tokens, no direct ledger write.
            token=self._issue(obs,'RETROACTIVE_SAME_EPOCH',['AUTHORIZE_OBSERVATION'],self._active_alias,parents=(self._active_alias,),
                reason=f'Confirmed at frame {current.frame}; same physical CandidateEpoch, no contradictory evidence')
            self.write('authorize_observation',token,obs);rows.append(obs)
        e={'confirmation_frame':current.frame,'candidate_epoch_id':current.candidate_id,
           'backfilled_start':min((o.time for o in rows),default=None),'backfilled_end':max((o.time for o in rows),default=None),
           'backfilled_observation_ids':[o.observation_id for o in rows],'reason':'SAME_CONFIRMED_CANDIDATE_EPOCH_CHECKED_EVIDENCE_ONLY'}
        self.backfill_events.append(e);return e
    def _authorize(self,obs,decision,new_alias=False,initial=False):
        super()._authorize(obs,decision,new_alias,initial)
        if decision!='CONTINUITY_AUTHORIZED' or not obs.vector:return
        p=self.recovery;core=[b for b in self._banks['core'] if b['active']];r=self.metadata[obs.observation_id]
        if len(core)>=p.maximum_core or obs.confidence<.6 or not clean(r):return
        if core and (obs.time-max(b['time'] for b in core)<.4-1e-5 or max(cosine(obs.vector,b['embedding']) for b in core)>=p.core_diversity):return
        recovered=self._active_alias!=self._aliases[0]['alias_id']
        if recovered:
            # Backfill is not future stabilization support.
            alias=next(a for a in self._aliases if a['alias_id']==self._active_alias)
            future=[x for x in self._ledger if x['active'] and x['alias_id']==self._active_alias and x['observation']['time']>alias['confirmation_time']]
            if len(future)<p.stabilization_frames or future[-1]['observation']['time']-alias['confirmation_time']<p.stabilization_seconds-1e-5:return
            # Only an independently older epoch can support recovered Core promotion.
            independent=[b for b in self._sources('core') if b['candidate_epoch_id']!=r['candidate_epoch_id'] and b['time']<r['candidate_epoch_start']]
            if not independent:return
            if self.photometric(r,independent)['state']=='STRONG_CONTRADICTION':return
            check=self.geometry(r,independent,self._sources('negative'),[cosine(obs.vector,b['embedding']) for b in independent],[])
            if check['state']!='CORE_STRONG_MATCH' or check.get('negative_positive'):return
        parents=[self._active_alias]+[b['entry_id'] for b in core]
        self._bank(obs,'core',self._active_alias,'trusted diverse continuity; stabilized after recovery' if recovered else 'trusted diverse initial-epoch continuity',parents)
        self.bank_events.append({'observation_id':obs.observation_id,'candidate_epoch_id':obs.candidate_id,'recovered':recovered,'parent_lineage':parents})
    def snapshot(self):
        s=super().snapshot();s.update(backfill_events=self.backfill_events,confirmation_audit=self.confirmation_audit,bank_events=self.bank_events)
        return s
