from bisect import bisect_right
from collections import defaultdict
import cv2
from ..video.reader import VideoReader


def render_video_v2(source, path, timelines, memory, events, samples):
    reader = VideoReader(source)
    metadata = reader.metadata
    size = (metadata.width//2*2, metadata.height//2*2)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), metadata.fps, size)
    if not writer.isOpened():
        raise RuntimeError("Cannot write V2 annotated video")
    entities = {e.track_id: e for e in memory.entities}
    by_frame = defaultdict(list)
    for track in timelines:
        for obs in track.observations:
            by_frame[obs.frame_index].append(obs)
    indices = [s.frame_index for s in samples]
    try:
        for info, frame in reader.frames():
            frame = cv2.resize(frame, size)
            sampled = indices[max(0, bisect_right(indices, info.frame_index)-1)]
            lines = [f"V2 | t={info.timestamp:.2f}s | sample={sampled/metadata.fps:.2f}s | RGB-relative",
                     "Semantics: VLM evidence only; unknown is unconfirmed. Labels are retrospective."]
            active = [e for e in events if e.start_time-1 <= info.timestamp <= e.end_time+1 and e.selected]
            lines.extend(f"EVENT {e.event_id} | {e.event_type}" for e in active[:2])
            cv2.rectangle(frame, (0, 0), (size[0], 22*len(lines)+12), (30, 30, 30), -1)
            for i, line in enumerate(lines):
                cv2.putText(frame, line, (8, 22*(i+1)), cv2.FONT_HERSHEY_SIMPLEX, .5, (240, 240, 240), 1, cv2.LINE_AA)
            occupied = []
            for obs in by_frame[sampled]:
                entity = entities.get(obs.track_id)
                semantic = entity.semantic_class if entity else "unadmitted"
                color = (230, 190, 90) if entity and semantic != "unknown" else (175, 175, 175)
                x1, y1, x2, y2 = map(int, obs.bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                label = f"ID:{obs.track_id} {semantic}"
                if semantic != obs.detector_class:
                    label += f" | YOLO? {obs.detector_class}"
                (w, h), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, .45, 1)
                x = max(0, min(x1, size[0]-w-6))
                y = max(22*len(lines)+h+18, y1-5)
                for _ in range(len(occupied)+1):
                    y = min(size[1]-base-5, y)
                    box = (x, y-h-3, x+w+5, y+base+2)
                    if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in occupied):
                        break
                    y += h+base+6
                occupied.append(box)
                cv2.rectangle(frame, box[:2], box[2:], (25, 25, 25), -1)
                cv2.putText(frame, label, (x+2, y), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1, cv2.LINE_AA)
            writer.write(frame)
    finally:
        writer.release()
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened() or int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) != metadata.frame_count:
            raise RuntimeError("V2 annotated video failed frame count check")
        cap.set(cv2.CAP_PROP_POS_FRAMES, metadata.frame_count-1)
        if not cap.read()[0]:
            raise RuntimeError("V2 annotated video final frame is unreadable")
    finally:
        cap.release()
