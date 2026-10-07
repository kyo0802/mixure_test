"""Three explicit recovery contexts. Visual similarity alone is never long-gap authority."""
def decide(visual,physical,policy):
    blockers=[]
    if physical['known_distinct']:blockers.append('KNOWN_DISTINCT_PHYSICAL_ENTITY')
    if physical['preexistence_contradiction']:blockers.append('PREEXISTING_DISTINCT_CANDIDATE')
    if physical['reachability']=='PHYSICALLY_INCONSISTENT':blockers.append('PHYSICAL_REACHABILITY_CONTRADICTION')
    if physical['interaction']=='INTERACTION_CONTINUITY_CONTRADICTION':blockers.append('INTERACTION_CONTEXT_CONTRADICTION')
    eligible=visual.get('route') in ['G','A'] and visual.get('stage')=='CONFIRMED_MATCH' and visual.get('integrity',{}).get('admissible',False) and visual.get('LightGlue',{}).get('state') in ['CORE_STRONG_MATCH','UNKNOWN']
    gap=physical['physical_continuity'].get('gap');long=gap is not None and gap>policy.continuity_horizon+.001
    if blockers:return {'stage':'REJECTED','confirmation_context':None,'blockers':blockers,'appearance_only_long_gap':False}
    if not eligible:return {'stage':visual['stage'] if visual['stage']!='CONFIRMED_MATCH' else 'PROVISIONAL','confirmation_context':None,'blockers':['VISUAL_MULTI_GATE_NOT_PASSED'],'appearance_only_long_gap':long and visual.get('DINOv3',{}).get('median',-1)>=.6}
    if not physical['unique_physical_support']:return {'stage':'AMBIGUOUS','confirmation_context':None,'blockers':['MULTIPLE_PHYSICALLY_PLAUSIBLE_CANDIDATES'],'appearance_only_long_gap':long}
    if physical['reachability']=='PHYSICALLY_CONSISTENT' and physical['candidate_continuity_valid'] and gap is not None and gap<=policy.continuity_horizon+.001:
        context='CONTINUITY_RECOVERY'
    elif physical['interaction']=='INTERACTION_CONTINUITY_SUPPORT' and visual.get('integrity',{}).get('admissible',False) and visual.get('LightGlue',{}).get('state') in ['CORE_STRONG_MATCH','UNKNOWN']:
        context='INTERACTION_CONDITIONED_RECOVERY'
    else:return {'stage':'AMBIGUOUS' if long else 'PROVISIONAL','confirmation_context':None,'blockers':['VISUAL_ONLY_WITHOUT_VALID_PHYSICAL_OR_INTERACTION_SUPPORT'],'appearance_only_long_gap':long}
    why=['CURRENT independent clean visual gates passed','No known-distinct/pre-existence/Negative/photometric contradiction',
        'Short compensated motion+scale+time continuity' if context=='CONTINUITY_RECOVERY' else 'Persistent reappearance near same live PersonEpoch with authorized-target occlusion lineage',
        'Unique physically plausible current candidate; only IdentityGuard may grant authorization']
    competitors='Known-distinct or physically inconsistent candidates excluded' if physical['competing_plausible_epochs']==[] else 'No uniquely excluded competitor: cannot confirm'
    return {'stage':'CONFIRMED_MATCH','confirmation_context':context,'blockers':[],'appearance_only_long_gap':False,
        'WHY_THIS_CANDIDATE_CAN_BE_PHONE_01':why,'WHY_COMPETING_CANDIDATES_ARE_NOT_PHONE_01':competitors}
