"""Currentness, independence, cleanliness and relevance; evidence only."""
from .io import stable

FLAGS=['SELF_EVIDENCE','SAME_LINEAGE_REFERENCE','CURRENT_FRAME_MISSING','CROSS_CANDIDATE_EPOCH_EVIDENCE',
       'OLD_FRAME_ONLY_CONFIRMATION','ANNOTATED_IMAGE_USED_FOR_REID','NEGATIVE_CONTRADICTION_IGNORED']

def provenance(row,identity_epoch=None,bank=None):
    p={'source_video':row['video_id'],'source_video_sha256':row.get('source_video_sha256'),'source_frame':row['frame'],'source_observation':row['observation_id'],
       'local_track':row.get('local_track_id',row.get('candidate_id')),'candidate_epoch':row.get('candidate_epoch_id'),
       'identity_epoch':identity_epoch,'crop_hash':row.get('crop_sha256'),'raw_image_hash':row.get('raw_image_sha256'),
       'raw_image_path':row.get('raw_image_path'),'raw_crop_path':row.get('raw_crop_path'),
       'annotation_overlays':row.get('annotation_overlays',True),'raw_source_verified':row.get('raw_source_verified',False),
       'timestamp':row['time'],'evidence_producer':row.get('evidence_producer','untrusted'),
       'bank_entry':bank.get('entry_id') if bank else None,'bank_lineage':bank.get('parent_lineage',[]) if bank else [],
       'alias_lineage':bank.get('alias_id') if bank else None,'authorization_lineage':bank.get('authorization_id') if bank else None}
    return {**p,'provenance_id':stable(p)}

def clean(row):
    return bool(row.get('raw_source_verified') and row.get('annotation_overlays') is False and row.get('crop_sha256') and row.get('raw_image_sha256') and row.get('raw_image_path') and row.get('raw_crop_path'))

def pair_integrity(candidate,reference,bank,current_observation_id,alias=None,ancestors=()):
    reasons=[];current=candidate['observation_id']==current_observation_id
    if not current:reasons+=['CURRENT_FRAME_MISSING','OLD_FRAME_ONLY_CONFIRMATION']
    selfpair=candidate['observation_id']==reference['observation_id'] or candidate.get('crop_sha256')==reference.get('crop_sha256')
    if selfpair:reasons.append('SELF_EVIDENCE')
    sameepoch=candidate.get('candidate_epoch_id')==reference.get('candidate_epoch_id')
    ancestor_ids=set(ancestors)|set(candidate.get('bank_ancestor_ids',[]))|set(candidate.get('candidate_alias_ids',[]))
    circular=bank.get('entry_id') in ancestor_ids or bank.get('alias_id') in ancestor_ids or bool(set(bank.get('parent_lineage',[])).intersection(ancestor_ids))
    if sameepoch or circular or alias and (bank.get('alias_id')==alias or alias in bank.get('parent_lineage',[])):reasons.append('SAME_LINEAGE_REFERENCE')
    predates=max(reference['time'],bank.get('created_time',reference['time']))<candidate.get('candidate_epoch_start',candidate['time'])-1e-6
    if not predates:reasons.append('CROSS_CANDIDATE_EPOCH_EVIDENCE')
    isclean=clean(candidate) and clean(reference)
    if not isclean:reasons.append('ANNOTATED_IMAGE_USED_FOR_REID')
    relevant=bool(bank.get('active') and bank.get('authorization_id') and bank.get('parent_lineage'))
    if not relevant:reasons.append('UNTRUSTED_OR_REVOKED_BANK')
    return {'admissible':not reasons,'current':current,'independent':not selfpair and not sameepoch and not circular and predates,
        'clean':isclean,'relevant':relevant,'rejection_reasons':reasons,
        'candidate_provenance':provenance(candidate),'reference_provenance':provenance(reference,bank.get('epoch_id'),bank)}

def candidate_integrity(rows,current):
    reasons=[]
    if not rows or rows[-1]['observation_id']!=current['observation_id']:reasons.append('CURRENT_FRAME_MISSING')
    if any(x.get('candidate_epoch_id')!=current.get('candidate_epoch_id') or x.get('video_id')!=current.get('video_id') for x in rows):reasons.append('CROSS_CANDIDATE_EPOCH_EVIDENCE')
    if any(not clean(x) for x in rows):reasons.append('ANNOTATED_IMAGE_USED_FOR_REID')
    if current.get('epoch_unresolved'):reasons.append('UNRESOLVED_CANDIDATE_DISCONTINUITY')
    return {'admissible':not reasons,'current':'CURRENT_FRAME_MISSING' not in reasons,'independent':True,
        'clean':'ANNOTATED_IMAGE_USED_FOR_REID' not in reasons,'relevant':True,'rejection_reasons':reasons,
        'provenance':[provenance(r) for r in rows]}
