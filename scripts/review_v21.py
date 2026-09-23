"""Generate raw and detector-overlay review frames without creating GT labels."""
import argparse
from pathlib import Path
import cv2
from memory_graph.v21.artifacts import read,sheet
from memory_graph.memory.memory_store import save_json


def review(video,output,seconds):
    output=Path(output); root=output/'gt_review'; root.mkdir(exist_ok=True)
    metadata=read(output/'event_analysis'/'video_metadata.json')
    tracks=read(output/'event_analysis'/'track_timelines.json')
    detections=read(output/'event_analysis'/'detections.json')
    cap=cv2.VideoCapture(str(video)); items=[]; template=[]
    for second in seconds:
        sample=min(metadata['sampled_frames'],key=lambda f:abs(f['timestamp']-second))
        index=sample['frame_index']; timestamp=sample['timestamp']
        cap.set(cv2.CAP_PROP_POS_FRAMES,index); ok,raw=cap.read()
        if not ok: raise RuntimeError(f'Cannot read {index}')
        cv2.imwrite(str(root/f'frame_{index:04d}_raw.jpg'),raw)
        overlay=raw.copy()
        for det in detections:
            if det['frame_index']!=index: continue
            x1,y1,x2,y2=map(int,det['bbox'])
            cv2.rectangle(overlay,(x1,y1),(x2,y2),(0,190,255),1)
            cv2.putText(overlay,det['class_name'],(x1,max(15,y1)),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,190,255),1)
        for track in tracks:
            for obs in track['observations']:
                if obs['frame_index']==index:
                    x1,y1,x2,y2=map(int,obs['bbox'])
                    cv2.putText(overlay,f"T{track['track_id']}",(x1,max(30,y1+16)),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,60,20),2)
        cv2.imwrite(str(root/f'frame_{index:04d}_detections.jpg'),overlay)
        items.append((raw,f'frame:{index} t:{timestamp:.3f}s'))
        template.append({'frame_index':index,'timestamp':timestamp,'gt_object_id':None,
            'visibility':'UNREVIEWED','bbox':None,'review_basis':'raw pixels; narrative is not frame-level GT'})
    cap.release()
    for i in range(0,len(items),8): sheet(items[i:i+8],root/f'sequence_{i//8+1:02d}.jpg',columns=2,size=(640,390))
    save_json(root/'annotation_template.json',{'status':'UNREVIEWED','samples':template,
        'allowed_visibility':['VISIBLE','PARTIALLY_VISIBLE','OCCLUDED','OUT_OF_VIEW','UNCERTAIN'],
        'instructions':'Only manually reviewed visible boxes enter recall. No interpolation of narrative times. bbox is original xyxy pixels.'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video');parser.add_argument('output');parser.add_argument('--seconds',nargs='+',type=float,default=list(range(0,31,2)))
    args=parser.parse_args();review(args.video,args.output,args.seconds)
