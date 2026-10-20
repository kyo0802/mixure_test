"""Display existing frozen citation pixels for AI review; no inference."""
import sys
sys.dont_write_bytecode=True
from consolidate_findmind_gt import ROOT,OUT,EXP,load_json,file_sha,save
sys.path.insert(0,str(ROOT/'outputs/current_development/video_event_experiment/.deps'))
from PIL import Image,ImageDraw
dest=OUT/'ai_visual_review/model_citations'
dest.mkdir(exist_ok=False)
near=load_json(OUT/'ai_visual_review/temporal_proximity_review.json')['pairs']
ids={r['proposal_id']:r for r in near}
windows={w['window_id']:w for w in load_json(EXP/'dataset.json')['windows']}
rows=[]
for p in load_json(EXP/'event_proposals.json')['proposals']:
    pid=f"{p['model']}:{p['window_id']}:{p['event_index']}"
    if pid not in ids:continue
    frames={f['alias']:f for f in windows[p['window_id']]['frames']}
    assert len(p['before_frames'])==len(p['after_frames'])==1
    rows.append(dict(ids[pid],type=p['type'],frames=[frames[p['before_frames'][0]],frames[p['after_frames'][0]]]))
for index in range(0,len(rows),3):
    chunk=rows[index:index+3]; canvas=Image.new('RGB',(1280,390*len(chunk)),'white');draw=ImageDraw.Draw(canvas)
    for i,row in enumerate(chunk):
        for j,f in enumerate(row['frames']):
            assert file_sha(ROOT/f['path'])==f['sha256']
            img=Image.open(ROOT/f['path']).convert('RGB');img.thumbnail((640,350))
            canvas.paste(img,(j*640,i*390+40))
            draw.text((j*640+5,i*390+2),f"#{index+i+1:02d} {row['proposal_id']} {row['type']} {'BEFORE' if j==0 else 'AFTER'}",fill='black')
            draw.text((j*640+5,i*390+19),f"{f['alias']} t={f['native_pts_s']:.4f} f{f['source_frame_index']}",fill='black')
        row['inspection_number']=index+i+1
        row['contact_sheet']=str((dest/f'page_{index//3+1:02d}.jpg').relative_to(ROOT))
    canvas.save(dest/f'page_{index//3+1:02d}.jpg',quality=94)
save(dest/'manifest.json',rows)
print(f'{len(rows)} citation pairs; {(len(rows)+2)//3} pages')
