"""Exact session-scoped source images and lightweight CPU overlays."""
import io
from pathlib import Path
from memory_graph.integration.adapters import sha
from .sessions import load_session


def scoped_file(root,session,reference):
    path=(Path(root)/reference).resolve()
    if not path.is_relative_to(session.resolve()) or not path.is_file():raise ValueError('Evidence outside selected session or missing')
    return path


def source_frame(root,identifier,index):
    session,manifest,_=load_session(root,identifier)
    f=next((f for f in manifest['frames'] if f['source_frame_index']==index),None)
    if not f:raise ValueError('No exact source frame in this session')
    path=scoped_file(root,session,f['path'])
    if sha(path)!=f['sha256']:raise ValueError('Source frame hash mismatch')
    if f['source_video_sha256']!=manifest['video']['source_sha256']:raise ValueError('Frame video mismatch')
    native=manifest['video']['frame_timeline'][index]
    if abs(native['source_time_s']-f['source_time_s'])>1e-9:raise ValueError('Frame native PTS mismatch')
    return f,path


def overlay(root,identifier,group):
    from PIL import Image,ImageDraw
    c=group['primary'];f,path=source_frame(root,identifier,c['source_frame_index'])
    session,_,_=load_session(root,identifier);image=Image.open(path).convert('RGB')
    if image.size!=(f['width'],f['height']):raise ValueError('Frame dimensions changed')
    for record in group['records']:
        if record['source_frame_index']!=f['source_frame_index'] or abs(record['source_time_s']-f['source_time_s'])>1e-9:
            raise ValueError('Candidate/evidence scope mismatch')
        for name,color in [('region_mask',(245,184,41)),('object_mask',(47,205,148))]:
            ref=record.get(name)
            if ref:
                mp=scoped_file(root,session,ref['path'])
                if sha(mp)!=ref['sha256']:raise ValueError('Mask hash mismatch')
                mask=Image.open(mp).convert('L')
                if mask.size!=image.size:raise ValueError('Mask geometry mismatch')
                alpha=mask.point(lambda x:55 if x else 0)
                color_image=Image.new('RGB',image.size,color)
                image=Image.composite(color_image,image,alpha)
    draw=ImageDraw.Draw(image)
    for record in group['records']:
        if record.get('region_polygon'):
            points=[tuple(p) for p in record['region_polygon']];draw.line(points+[points[0]],fill='#f5b829',width=4)
        if record.get('object_bbox'):draw.rectangle(record['object_bbox'],outline='#2fcd94',width=4)
    buffer=io.BytesIO();image.save(buffer,format='PNG')
    return dict(png=buffer.getvalue(),original=path.read_bytes(),frame=f,reference=str(path.relative_to(session)))


def source_video(root,identifier):
    _,manifest,_=load_session(root,identifier);v=manifest['video'];path=Path(v['source_path']).resolve()
    if not path.is_relative_to(Path(root).resolve()) or path.suffix.lower()!='.mp4' or not path.is_file():
        raise ValueError('Source video unavailable inside approved project directory; source frames remain available')
    if sha(path)!=v['source_sha256']:raise ValueError('Source video hash mismatch')
    return path
