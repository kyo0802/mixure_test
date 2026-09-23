from pathlib import Path
import cv2
import numpy as np
from .models import Keyframe
from ..video.reader import VideoReader


def score_candidates(samples, timelines):
    by_frame = {}
    for track in timelines:
        for obs in track.observations:
            by_frame.setdefault(obs.frame_index, []).append(obs)
    return by_frame


def save_track_crops(directory, frames, supplied, images, by_frame):
    """Identity reference only: crop layout is never spatial/temporal evidence."""
    width, height, columns = 320, 264, 3
    sheet = np.full((max(1, (len(supplied)+columns-1)//columns)*height, columns*width, 3), 245, dtype=np.uint8)
    records = []
    for index, tid in enumerate(supplied):
        candidates = [(frame, obs) for frame in frames for obs in by_frame.get(frame.frame_index, []) if obs.track_id == tid]
        frame, obs = max(candidates, key=lambda pair: pair[1].area_fraction*pair[1].confidence)
        source = images[frame.frame_index]
        x1,y1,x2,y2 = obs.bbox
        pad = .04*max(x2-x1,y2-y1)
        left,top = max(0,int(x1-pad)),max(0,int(y1-pad))
        right,bottom = min(source.shape[1],int(np.ceil(x2+pad))),min(source.shape[0],int(np.ceil(y2+pad)))
        crop = source[top:bottom,left:right]
        scale = min((width-8)/crop.shape[1],(height-32)/crop.shape[0])
        crop = cv2.resize(crop,(max(1,int(crop.shape[1]*scale)),max(1,int(crop.shape[0]*scale))))
        x,y = (index%columns)*width,(index//columns)*height
        sheet[y+28:y+28+crop.shape[0],x+4:x+4+crop.shape[1]] = crop
        cv2.putText(sheet,f'ID:{tid} | {frame.phase} {frame.timestamp:.2f}s',(x+6,y+20),
                    cv2.FONT_HERSHEY_SIMPLEX,.48,(20,20,20),1,cv2.LINE_AA)
        records.append({'track_id':tid,'phase':frame.phase,'timestamp':frame.timestamp,
                        'source_frame_index':frame.frame_index,'crop_bbox':[left,top,right,bottom]})
    if not cv2.imwrite(str(directory/'track_crops.jpg'),sheet):
        raise RuntimeError('Failed to save grounded track crop reference')
    from ..memory.memory_store import save_json
    save_json(directory/'track_crops.json',{'purpose':'identity only; tile layout is not scene geometry','crops':records})


def select_keyframes(event, samples, by_frame, sharpness, duration, event_config, config):
    selected = []
    targets = {"before": max(0, event.peak_time-event_config.before_offset_seconds), "during": event.peak_time,
               "after": min(samples[-1].timestamp, event.peak_time+event_config.after_offset_seconds)}
    involved = set(event.involved_track_ids)
    for phase, desired in targets.items():
        phase_samples = [s for s in samples if (phase == "during" or
            (phase == "before" and s.timestamp < event.peak_time) or (phase == "after" and s.timestamp > event.peak_time))]
        notes = []
        if not phase_samples:
            phase_samples = [samples[0] if phase == "before" else samples[-1]]
            notes.append("video boundary: distinct phase frame unavailable")
        candidates = [s for s in phase_samples if abs(s.timestamp-desired) <= config.search_radius_seconds]
        if not candidates:
            candidates = [min(phase_samples, key=lambda s: abs(s.timestamp-desired))]
        visible_candidates = [s for s in candidates if involved & {o.track_id for o in by_frame.get(s.frame_index, [])}]
        if config.require_involved_track_visibility and visible_candidates:
            candidates = visible_candidates
        elif config.require_involved_track_visibility:
            notes.append("involved tracks absent in this phase; absence evidence retained")
        def quality(sample):
            obs = [o for o in by_frame.get(sample.frame_index, []) if o.track_id in involved]
            visibility = len(obs)/max(1, len(involved))
            area = min(1, sum(o.area_fraction for o in obs)/.15)
            confidence = np.mean([o.confidence for o in obs]) if obs else 0
            focus = min(1, sharpness.get(sample.frame_index, 0)/200)
            return (config.visibility_weight*visibility + config.bbox_area_weight*area +
                config.detector_confidence_weight*confidence + config.sharpness_weight*focus - .1*abs(sample.timestamp-desired))
        best = max(candidates, key=quality)
        selected.append(Keyframe(phase=phase, frame_index=best.frame_index, timestamp=best.timestamp,
            desired_timestamp=desired, image_path=f"{phase}.jpg", visible_track_ids=[], supplied_track_ids=[],
            sharpness=sharpness.get(best.frame_index, 0), selection_score=quality(best), notes=notes))
    # Phase searches may shift the DURING frame; choose the peak-nearest frame if ordering would invert.
    if not selected[0].timestamp <= selected[1].timestamp <= selected[2].timestamp:
        peak = min(samples, key=lambda s: abs(s.timestamp-event.peak_time))
        selected[1].frame_index, selected[1].timestamp = peak.frame_index, peak.timestamp
        selected[1].notes.append("during frame restored to nearest peak to preserve phase order")
    return selected


def prepare_windows(source, output, events, timelines, metadata, config):
    # Decode sampled images once. These short prototype clips fit in memory; images are released after windows are saved.
    images = {info.frame_index: frame for info, frame in VideoReader(source).frames(config.perception.video.sample_fps)}
    sharpness = {index: float(cv2.Laplacian(cv2.cvtColor(cv2.resize(image, (320, 180)), cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
                 for index, image in images.items()}
    by_frame = score_candidates(metadata.sampled_frames, timelines)
    windows = {}
    for event in events:
        if not event.selected:
            continue
        directory = Path(output)/"events"/event.event_id
        directory.mkdir(parents=True, exist_ok=True)
        frames = select_keyframes(event, metadata.sampled_frames, by_frame, sharpness, metadata.duration, config.events, config.keyframes)
        union = {o.track_id for frame in frames for o in by_frame.get(frame.frame_index, [])}
        # Only supply IDs that actually appear in at least one image; retain original involved IDs in event metadata.
        priority = sorted(union, key=lambda tid: (tid not in event.involved_track_ids,
            -sum(o.confidence*o.area_fraction for f in frames for o in by_frame.get(f.frame_index, []) if o.track_id == tid), tid))
        supplied = priority[:config.keyframes.max_context_tracks]
        save_track_crops(directory, frames, supplied, images, by_frame)
        for keyframe in frames:
            image = images[keyframe.frame_index]
            scale = min(1, config.keyframes.image_width/image.shape[1])
            image = cv2.resize(image, (int(image.shape[1]*scale), int(image.shape[0]*scale)))
            visible = [o for o in by_frame.get(keyframe.frame_index, []) if o.track_id in supplied]
            for obs in visible:
                x1, y1, x2, y2 = [int(v*scale) for v in obs.bbox]
                color = (90, 230, 245)
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 1)
                label = f"ID:{obs.track_id}"
                y = max(22, y1-4)
                width = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, .65, 2)[0][0]
                cv2.rectangle(image, (x1, y-19), (min(image.shape[1]-1, x1+width+4), y+4), (30, 30, 30), -1)
                cv2.putText(image, label, (x1+2, y), cv2.FONT_HERSHEY_SIMPLEX, .65, color, 2, cv2.LINE_AA)
            keyframe.visible_track_ids = [o.track_id for o in visible]
            keyframe.supplied_track_ids = supplied
            if set(event.involved_track_ids)-set(supplied):
                keyframe.notes.append("some involved tracks unavailable or omitted by context limit; never supplied to VLM")
            cv2.putText(image, f"{keyframe.phase.upper()} {keyframe.timestamp:.2f}s", (10, image.shape[0]-12),
                        cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2, cv2.LINE_AA)
            if not cv2.imwrite(str(directory/keyframe.image_path), image):
                raise RuntimeError("Failed to save event input image")
        windows[event.event_id] = frames
    return windows
