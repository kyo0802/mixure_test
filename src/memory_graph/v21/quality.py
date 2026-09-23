"""Track diagnostics and appearance evidence, independent of event selection."""
from collections import Counter
import cv2
import numpy as np


def crop_frame(image, bbox):
    x1,y1,x2,y2 = bbox
    return image[max(0,int(y1)):min(image.shape[0],int(np.ceil(y2))),
                 max(0,int(x1)):min(image.shape[1],int(np.ceil(x2)))].copy()


def descriptor(crop):
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0,1,2], None, [8,4,4], [0,180,0,256,0,256]).flatten()
    hist /= max(float(hist.sum()), 1)
    return hist.tolist()


def similarity(a, b):
    if a is None or b is None:
        return None
    return float(np.clip(np.sqrt(np.asarray(a)*np.asarray(b)).sum(), 0, 1))


def measure(track, appearances, sample_period, config):
    obs = track.observations
    times = np.array([o.timestamp for o in obs])
    steps = np.diff(times)
    centers = np.array([o.normalized_center for o in obs])
    jumps = np.linalg.norm(np.diff(centers, axis=0), axis=1)
    speeds = jumps/np.maximum(steps, 1e-6)
    acceleration = np.abs(np.diff(speeds))
    gaps = [dict(start=obs[i].timestamp, end=obs[i+1].timestamp,
                 missing_seconds=float(dt-sample_period)) for i,dt in enumerate(steps) if dt>sample_period*1.6]
    app_scores = [similarity(a,b) for a,b in zip(appearances,appearances[1:])]
    app_scores = [x for x in app_scores if x is not None]
    semantic = Counter(o.detector_class for o in obs)
    duration = float(times[-1]-times[0])
    usable = len(obs)>=config.min_observations and duration>=config.min_duration and track.mean_detector_confidence>=config.min_confidence
    abrupt = int(sum(jumps>.25))
    flags = []
    if not usable:
        flags.append('TOO_SHORT' if len(obs)<config.min_observations or duration<config.min_duration else 'INSUFFICIENT_EVIDENCE')
    if gaps: flags.append('FRAGMENTED')
    if abrupt: flags += ['UNSTABLE', 'POSSIBLE_ID_SWITCH']
    if app_scores and min(app_scores)<.35: flags.append('UNSTABLE')
    return {'track_id':track.track_id,'duration':duration,'observation_count':len(obs),
        'usable_for_identity':usable,'flags':sorted(set(flags)) or ['GOOD'],
        'detector_gaps':gaps,'gap_duration':sum(g['missing_seconds'] for g in gaps),
        'max_center_jump':float(max(jumps,default=0)), 'abrupt_jumps':abrupt,
        'motion_speed_change_mean':float(np.mean(acceleration)) if len(acceleration) else None,
        'semantic_consistency':max(semantic.values())/len(obs),
        'appearance_consistency':float(np.mean(app_scores)) if app_scores else None,
        'appearance_samples':len(appearances), 'fragmentation_context':[],
        'note':'Diagnostic flags only; gaps/jumps do not establish a ground-truth ID switch.'}
