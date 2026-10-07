"""IdentityGuard policy extension. Capability/mutation/epoch/revocation authority is inherited verbatim."""
from memory_graph.identity.guard import IdentityGuard
from memory_graph.identity.contracts import cosine
from .evidence import TrackletIdentityEvidenceAccumulator,RecoveryPolicy


class V295IdentityGuard(IdentityGuard):
    def __init__(self,policy=None,*,recovery_policy=None,metadata=None,verifier=None):
        super().__init__(policy)
        self.recovery_policy=recovery_policy or RecoveryPolicy()
        self.accumulator=TrackletIdentityEvidenceAccumulator(self.recovery_policy,metadata)
        self.verifier=verifier;self.bank_events=[]

    def _candidate_decision(self,obs,current):
        # Metadata cannot grant this flag: it is overwritten from Guard's live alias state.
        for x in current:
            meta=self.accumulator.metadata.setdefault(x.observation_id,{})
            meta['authorized_target']=any(a['candidate_id']==x.candidate_id and a['status']=='CONFIRMED' for a in self._aliases)
        result=self.accumulator.evaluate(obs.candidate_id,self._candidates[obs.candidate_id],self._banks['core'],
            self._banks['negative'],current,bool(self._epoch() and self._epoch()['end_time'] is not None),self.verifier)
        # Stage names describe evidence; inherited Guard is still the only authorization issuer.
        decision=result['stage'];record={**result,'decision':decision,'reason':'V295_EXPLICIT_MULTIFRAME_AND_GEOMETRY_GATES',
                                       'observation_id':obs.observation_id,'epoch_id':self._epoch()['epoch_id'] if self._epoch() else None}
        self._decisions.append(record)
        if decision=='CONFIRMED_MATCH':
            self._new_epoch(obs,'MULTI_EVIDENCE_REIDENTIFICATION')
            self._authorize(obs,'CONFIRMED_MATCH',new_alias=True)
        elif decision=='PROVISIONAL' and obs.vector and self._epoch():
            if not any(b['candidate_id']==obs.candidate_id and b['active'] for b in self._banks['quarantine']):
                self._bank(obs,'quarantine',None,'PROVISIONAL; no Core authority',[b['entry_id'] for b in self._banks['core'] if b['active']])
        return decision

    def _authorize(self,obs,decision,new_alias=False,initial=False):
        super()._authorize(obs,decision,new_alias=new_alias,initial=initial)
        if decision!='CONTINUITY_AUTHORIZED' or not obs.vector:return
        p=self.recovery_policy;core=[b for b in self._banks['core'] if b['active']]
        if len(core)>=p.maximum_core_views or obs.confidence<p.minimum_bank_quality:return
        if core and (obs.time-max(b['time'] for b in core)<.4-1e-5 or
                     max(cosine(obs.vector,b['embedding']) for b in core)>=p.core_diversity_cosine):return
        alias=next(a for a in self._aliases if a['alias_id']==self._active_alias)
        ledger=[r for r in self._ledger if r['active'] and r['alias_id']==self._active_alias]
        recovered=alias['alias_id']!=self._aliases[0]['alias_id']
        if recovered:
            times=[r['observation']['time'] for r in ledger]
            stabilized=len(times)>=p.stabilization_frames and max(times)-min(times)>=p.stabilization_span-1e-5
            if not stabilized:return
            if not self.verifier:return
            scores=[[cosine(obs.vector,b['embedding']) for b in core]]
            neg=[b for b in self._banks['negative'] if b['active']]
            check=self.verifier([obs],core,neg,scores,[[cosine(obs.vector,b['embedding']) for b in neg]])
            if not check.get('core_positive') or check.get('negative_positive'):return
        parents=[self._active_alias]+[b['entry_id'] for b in core]
        self._bank(obs,'core',self._active_alias,'CONTINUITY_AUTHORIZED diverse view; stabilized reauthorization' if recovered else
                   'CONTINUITY_AUTHORIZED diverse view in trusted epoch',parents)
        self.bank_events.append({'observation_id':obs.observation_id,'frame':obs.frame,'alias_id':self._active_alias,
                                 'recovered_stabilized':recovered,'reason':'quality + temporal separation + appearance view diversity',
                                 'parent_lineage':parents})

    def snapshot(self):
        result=super().snapshot();result['v295_bank_events']=list(self.bank_events)
        result['v295_recovery_policy']=__import__('dataclasses').asdict(self.recovery_policy)
        return result
