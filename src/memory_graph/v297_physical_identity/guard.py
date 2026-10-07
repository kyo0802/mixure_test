"""Physical policy extension; authority/mutation/revocation sinks inherited verbatim."""
from memory_graph.identity.guard import IdentityGuard
from memory_graph.v296_reid.guard import V296IdentityGuard
from .policy import decide

class V297IdentityGuard(V296IdentityGuard):
    def __init__(self,policy,recovery,metadata,v2,geometry,photometric,physical):
        super().__init__(policy,recovery,metadata,v2,geometry,photometric);self.physical=physical;self.physical_decisions=[]
    def process(self,timestamp,observations):
        obs=list(observations)
        if self._last:
            bad=next((o for o in obs if o.candidate_id==self._last.candidate_id and any([self.metadata[o.observation_id]['physical_identity_evidence']['known_distinct'],self.metadata[o.observation_id]['physical_identity_evidence']['preexistence_contradiction'],self.metadata[o.observation_id]['physical_identity_evidence']['reachability']=='PHYSICALLY_INCONSISTENT'])),None)
            if bad:
                prior_now=self._now;self._now=timestamp
                if self._active_alias!=self._aliases[0]['alias_id']:
                    tok=self._issue(bad,'REVOKED',['REVOKE_ALIAS'],self._active_alias,reason='V297_PHYSICAL_IDENTITY_CONTRADICTION');self.write('revoke_alias',tok,bad)
                else:self._close('V297_PHYSICAL_CONTINUITY_CONTRADICTION')
                self._now=prior_now
        return super().process(timestamp,obs)
    def _candidate_decision(self,obs,current):
        histories=[self.metadata[o.observation_id] for o in self._candidates[obs.candidate_id]]
        histories[-1]['candidate_alias_ids']=[a['alias_id'] for a in self._aliases if a['candidate_id']==obs.candidate_id]
        current_rows=[self.metadata[o.observation_id] for o in current]
        for r in current_rows:r['authorized_target']=bool(self._last and self._last.candidate_id==r['candidate_epoch_id'])
        visual=self.accumulator.evaluate(histories,self._sources('core'),self._sources('negative'),current_rows,
            bool(self._epoch() and self._epoch()['end_time'] is not None),self.v2,self.geometry,self.photometric)
        physical=self.metadata[obs.observation_id]['physical_identity_evidence'];selection=decide(visual,physical,self.physical.policy)
        contaminated=[r['observation_id'] for r in histories if r['physical_identity_evidence']['known_distinct'] or r['physical_identity_evidence']['preexistence_contradiction']]
        if contaminated:selection={'stage':'REJECTED','confirmation_context':None,'blockers':['SAME_CANDIDATE_EPOCH_HAS_KNOWN_DISTINCT_HISTORY'],'appearance_only_long_gap':False,'contradictory_observation_ids':contaminated}
        record={**visual,**selection,'visual_proposal_stage':visual['stage'],'visual_route':visual['route'],'physical_identity':physical,
            'decision':selection['stage'],'observation_id':obs.observation_id,'epoch_id':self._epoch()['epoch_id'] if self._epoch() else None,
            'reason':'V297_EXPLICIT_VISUAL_AND_PHYSICAL_IDENTITY_GATES'}
        self._decisions.append(record);self.physical_decisions.append(record)
        if selection['stage']=='CONFIRMED_MATCH':
            self._new_epoch(obs,'V297_'+selection['confirmation_context']);self._authorize(obs,'CONFIRMED_MATCH',new_alias=True)
            aid=self._ledger[-1]['authorization_id'];backfill=self._backfill(obs,record)
            record.update(identity_epoch_id=self._epoch()['epoch_id'],authorization_capability=aid,alias_id=self._active_alias,backfill=backfill)
            self.confirmation_audit.append(record)
        elif selection['stage']=='PROVISIONAL' and self._epoch() and not any(b['active'] and b['candidate_id']==obs.candidate_id for b in self._banks['quarantine']):
            self._bank(obs,'quarantine',None,'V297 provisional; no physical identity authorization',[b['entry_id'] for b in self._banks['core'] if b['active']])
        return selection['stage']
    def _bank(self,obs,kind,alias,reason,parents=()):
        if kind=='negative' and not self.physical.distinct_link(self.metadata[obs.observation_id])['matched']:return
        return super()._bank(obs,kind,alias,reason,parents)
    def _authorize(self,obs,decision,new_alias=False,initial=False):
        if decision=='CONTINUITY_AUTHORIZED' and self._aliases and self._active_alias!=self._aliases[0]['alias_id']:
            p=self.metadata[obs.observation_id]['physical_identity_evidence']
            if p['reachability']!='PHYSICALLY_CONSISTENT' or p['known_distinct'] or not p['unique_physical_support']:
                return IdentityGuard._authorize(self,obs,decision,new_alias,initial)
        return super()._authorize(obs,decision,new_alias,initial)
    def _backfill(self,current,result):
        indexes=[]
        for i,oid in enumerate(result['observation_ids']):
            p=self.metadata[oid]['physical_identity_evidence']
            if not p['known_distinct'] and not p['preexistence_contradiction'] and p['reachability']!='PHYSICALLY_INCONSISTENT' and p['interaction']!='INTERACTION_CONTINUITY_CONTRADICTION':indexes.append(i)
        filtered={**result,'observation_ids':[result['observation_ids'][i] for i in indexes],
            'DINOv3':{**result['DINOv3'],'per_frame':[result['DINOv3']['per_frame'][i] for i in indexes]},
            'DINOv2_matrix':[result['DINOv2_matrix'][i] for i in indexes]}
        return super()._backfill(current,filtered)
    def snapshot(self):
        s=super().snapshot();s['physical_identity_state']=self.physical.snapshot();s['physical_decisions']=self.physical_decisions;return s
