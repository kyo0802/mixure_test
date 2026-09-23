import json
from pathlib import Path
import cv2
import numpy as np
from ..memory.memory_store import save_json
from .quality import crop_frame, descriptor


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sheet(items, path, columns=3, size=(320,250)):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    w,h=size
    canvas=np.full((max(1,(len(items)+columns-1)//columns)*h,columns*w,3),245,np.uint8)
    for index,(image,label) in enumerate(items):
        x,y=(index%columns)*w,(index//columns)*h
        cv2.putText(canvas,label[:65],(x+5,y+20),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,0,0),1,cv2.LINE_AA)
        if image.size:
            scale=min((w-8)/image.shape[1],(h-32)/image.shape[0])
            small=cv2.resize(image,(max(1,int(image.shape[1]*scale)),max(1,int(image.shape[0]*scale))))
            canvas[y+28:y+28+small.shape[0],x+4:x+4+small.shape[1]]=small
    if not cv2.imwrite(str(path),canvas): raise RuntimeError(f'Cannot write {path}')


def track_artifacts(source, tracks, output):
    cap=cv2.VideoCapture(str(source)); features={}; selected={}; crops={}
    for track in tracks:
        indices=sorted(set(np.linspace(0,len(track.observations)-1,min(6,len(track.observations))).astype(int)))
        items=[]; features[track.track_id]=[]; selected[track.track_id]=[]
        for idx in indices:
            obs=track.observations[idx]
            cap.set(cv2.CAP_PROP_POS_FRAMES,obs.frame_index); ok,image=cap.read()
            if not ok: raise RuntimeError(f'Cannot decode frame {obs.frame_index}')
            crop=crop_frame(image,obs.bbox)
            features[track.track_id].append(descriptor(crop))
            items.append((crop,f'ID:{track.track_id} frame:{obs.frame_index} t:{obs.timestamp:.2f}s'))
            selected[track.track_id].append({'frame_index':obs.frame_index,'timestamp':obs.timestamp,'bbox':obs.bbox})
        directory=Path(output)/'tracklets'/f'track_{track.track_id}'
        sheet(items,directory/'contact_sheet.jpg')
        save_json(directory/'tracklet.json',{'track':track,'appearance_samples':selected[track.track_id]})
        crops[track.track_id]=items
    cap.release()
    return features,crops


def entity_artifacts(entities,crops,output):
    for e in entities:
        path=Path(output)/'entities'/e.entity_id
        sheet([item for tid in e.local_track_ids for item in crops[tid]],path/'contact_sheet.jpg')
        save_json(path/'entity.json',e)
        save_json(path/'association_history.json',e.association_history)
