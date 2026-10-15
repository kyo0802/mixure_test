"""New CPU-authored stylized scenes; designer intent is not physical event GT."""
import support as s
import math,random,hashlib,io
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

WIDTH,HEIGHT=1280,720
SEED_BASE=202610150370

def specification(number):
    reps=['MULTI_IMAGE','MULTI_IMAGE','MULTI_IMAGE','STORYBOARD','STORYBOARD','STORYBOARD','NATIVE_VIDEO_ARRAY','NATIVE_VIDEO_ARRAY']
    strata=[0,1,2,0,1,2,0,1]
    seed=SEED_BASE+number*1709
    sid='S_'+hashlib.sha256(f'V1D_NEW_SCENE|{seed}|{number}'.encode()).hexdigest()[:16]
    # Each scenario has its own geometry/palette, fixed before the task candidate.
    return {'condition_id':f'C{number:02d}','scenario_id':sid,'representation':reps[number-1],
      'intended_event_count_private':strata[number-1],'seed':seed,'dimensions':[WIDTH,HEIGHT],
      'phone_anchor_x':435+(number*37)%190,'desk_palette':[118+number*7,136+number*3,129+number*2],
      'phone_color':[28+number*6,42+number*3,66+number*4],'phone_width':142+number*3,
      'frame_timestamps_s':[i*.5 for i in range(8)],'origin':'fresh procedural source; no real/old pixels or GT used'}

def poses(number):
    # (horizontal offset, lift in pixels, visible grasp). Newly authored phases,
    # not extracted from historical videos, model responses or old fixtures.
    if number==1:return [(0,0,False)]*8
    if number==4:return [(42,128,True)]*8
    if number==7:return [(-23,0,False)]*8
    if number==2:return [(0,0,False),(0,0,True),(8,27,True),(20,79,True),(38,132,True),(64,168,True),(82,169,True),(94,170,True)]
    if number==5:return [(91,171,True),(80,154,True),(64,122,True),(40,77,True),(16,31,True),(0,0,True),(0,0,False),(0,0,False)]
    if number==8:return [(-13,0,False),(-13,0,False),(-13,0,True),(-1,42,True),(26,105,True),(56,166,True),(77,172,True),(85,172,True)]
    if number==3:return [(0,0,False),(0,0,True),(22,89,True),(83,161,True),(135,154,True),(176,72,True),(200,0,True),(200,0,False)]
    return [(57,163,True),(35,86,True),(0,0,True),(0,0,False),(0,0,True),(-30,67,True),(-65,141,True),(-79,166,True)]

def render(config,number,index):
    seed=config['seed'];rng=random.Random(seed)
    yy,xx=np.mgrid[:HEIGHT,:WIDTH]
    noise=np.random.default_rng(seed+811).integers(-3,4,(HEIGHT,WIDTH,1))
    rgb=np.zeros((HEIGHT,WIDTH,3),dtype=np.int16)
    for c,base in enumerate([218+number,226-number,225]):rgb[:,:,c]=base-yy//60
    desk=yy>=350
    for c,base in enumerate(config['desk_palette']):rgb[:,:,c][desk]=base+((xx//11+yy//23)%7)[desk]
    im=Image.fromarray(np.clip(rgb+noise,0,255).astype(np.uint8));d=ImageDraw.Draw(im)
    # Fixed wall shelf, desk edge, notebook, cup and plant: meaningful scenery.
    d.rectangle((0,345,WIDTH,359),fill=(91,103,100))
    d.rounded_rectangle((77,101,303,233),radius=6,fill=(231,222,203),outline=(136,143,138),width=5)
    d.line((91,214,284,130),fill=(115,143,150),width=10)
    d.polygon([(925,506),(1180,545),(1117,613),(865,570)],fill=(74,88,117),outline=(46,55,76))
    d.line((943,520,1138,550),fill=(197,203,204),width=3)
    mugx=178+number*6
    d.ellipse((mugx-62,438,mugx+65,466),fill=(76,91,84))
    d.rounded_rectangle((mugx-46,368,mugx+37,449),radius=14,fill=(229,218,193),outline=(128,136,122),width=3)
    d.arc((mugx+19,376,mugx+77,431),270,90,fill=(229,218,193),width=12)
    d.ellipse((mugx-44,359,mugx+35,385),fill=(238,229,208),outline=(128,136,122),width=3)
    d.ellipse((mugx-33,365,mugx+23,379),fill=(91,65,44))
    d.polygon([(1078,303),(1164,303),(1150,363),(1091,363)],fill=(174,122,95))
    for k in range(5):
        x=1116+int(math.cos(k*1.7)*44);y=240+k*7
        d.line((1120,311,x,y),fill=(60,111,83),width=5)
        d.ellipse((x-23,y-14,x+21,y+17),fill=(66+5*k,118+3*k,89))
    dx,lift,grasp=poses(number)[index];x=config['phone_anchor_x']+dx;y=510-lift;w=config['phone_width']
    shadow=Image.new('RGBA',im.size);sd=ImageDraw.Draw(shadow)
    sd.ellipse((x-14,535,x+w+35,566),fill=(15,28,24,max(28,98-lift//2)))
    im=Image.alpha_composite(im.convert('RGBA'),shadow.filter(ImageFilter.GaussianBlur(10+lift/16))).convert('RGB');d=ImageDraw.Draw(im)
    # Palm/forearm behind phone; fingers then wrap its visible right edge.
    if grasp:
        skin=(210-number*2,165-number,131)
        d.polygon([(x+w-17,y-27),(x+w+113,y-12),(x+w+247,y+116),(x+w+182,y+163),(x+w+43,y+43)],fill=skin,outline=(164,119,95))
    d.rounded_rectangle((x,y-62,x+w,y+20),radius=13,fill=tuple(config['phone_color']),outline=(15,24,31),width=4)
    d.rounded_rectangle((x+8,y-55,x+w-8,y+13),radius=9,fill=(43,74+number*2,91+number*3),outline=(105,129,136),width=2)
    d.polygon([(x+16,y-48),(x+w//2,y-48),(x+w-19,y+5),(x+w//2-20,y+5)],fill=(70,103,117))
    d.ellipse((x+w//2-3,y-54,x+w//2+4,y-47),fill=(11,20,29))
    d.line((x+w//2-15,y+6,x+w//2+15,y+6),fill=(171,193,200),width=3)
    if grasp:
        for k in range(3):
            fy=y-41+k*19
            d.rounded_rectangle((x+w-17,fy,x+w+47-k*5,fy+17),radius=8,fill=skin,outline=(164,119,95),width=2)
        d.ellipse((x+w-31,y+3,x+w+17,y+29),fill=skin,outline=(164,119,95),width=2)
    return im

def generate():
    assert (s.OUT/'SCHEMA_AUDIT.json').exists()
    assert not (s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt').exists()
    configs=[specification(i) for i in range(1,9)]
    # Rank within modality, then round-robin: interleaved without answer quality.
    buckets={r:sorted([c for c in configs if c['representation']==r],key=lambda c:hashlib.sha256(('V1D_ORDER_V1|'+c['scenario_id']).encode()).hexdigest())
      for r in ['MULTI_IMAGE','STORYBOARD','NATIVE_VIDEO_ARRAY']}
    order=[]
    for index in range(3):
        for rep in ['MULTI_IMAGE','STORYBOARD','NATIVE_VIDEO_ARRAY']:
            if index<len(buckets[rep]):order.append(buckets[rep][index]['scenario_id'])
    old_hashes=set(s.read(s.REF/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json')['model_visible_frames_sha256'].values())
    cap=s.ROOT/'artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/fixture_hash_inventory.json'
    old_hashes.update(s.read(cap).values())
    all_assets={};scenarios=[];all_frames=[]
    for number,config in enumerate(configs,1):
        fid=config['scenario_id'];frames=[];images=[]
        for i in range(8):
            im=render(config,number,i);path=s.OUT/'media'/fid/f'F{i+1:04d}.png'
            path.parent.mkdir(parents=True,exist_ok=True)
            encoded=io.BytesIO();im.save(encoded,format='PNG',optimize=False)
            if path.exists():
                assert path.read_bytes()==encoded.getvalue(),'Partial-render resume must preserve exact original pixels'
            else:
                with path.open('xb') as f:f.write(encoded.getvalue())
            digest=s.sha(path)
            assert digest not in old_hashes
            with Image.open(path) as verified:
                assert verified.size==(WIDTH,HEIGHT) and verified.mode=='RGB'
                # Palette size is not a content/blankness test. Keep the actual
                # pixels unchanged; test contrast and spatial edges instead.
                arr=np.asarray(verified).astype(np.int16)
                assert float(arr.std())>20
                assert int((np.abs(np.diff(arr,axis=1)).sum(axis=2)>20).sum())>500
                assert not verified.info
            row={'filename':path.relative_to(s.OUT).as_posix(),'sha256':digest,'rgb_sha256':hashlib.sha256(im.tobytes()).hexdigest(),
              'alias':f'F{i+1:04d}','synthetic_timestamp_s':i*.5,'source_frame_position':i}
            frames.append(row);images.append(im);all_frames.append(im.copy());all_assets[row['filename']]=digest
        canvas=Image.new('RGB',(1440,906),'white');draw=ImageDraw.Draw(canvas)
        for i,(im,row) in enumerate(zip(images,frames)):
            x=i%3*480;y=i//3*302;canvas.paste(im.resize((480,270),Image.Resampling.LANCZOS),(x,y+32))
            draw.text((x+8,y+8),row['alias'],fill='black',font=ImageFont.load_default())
        path=s.OUT/'media'/fid/'STORYBOARD.png'
        encoded=io.BytesIO();canvas.save(encoded,format='PNG',optimize=False)
        if path.exists():assert path.read_bytes()==encoded.getvalue()
        else:
            with path.open('xb') as f:f.write(encoded.getvalue())
        all_assets[path.relative_to(s.OUT).as_posix()]=s.sha(path)
        scenarios.append({**config,'frames':frames,'storyboard':{'filename':path.relative_to(s.OUT).as_posix(),'sha256':s.sha(path)},
          'rendered_object_state_sequence_private':poses(number),'rendering_limits':'stylized 2D/depth cues, not independently adjudicated physical GT'})
        print('FIXTURE_GENERATED',fid,config['representation'],flush=True)
    sheet=Image.new('RGB',(8*320,8*180),'white')
    for i,im in enumerate(all_frames):sheet.paste(im.resize((320,180)),((i%8)*320,(i//8)*180))
    path=s.OUT/'media'/'technical_contact_sheet.png'
    with path.open('xb') as f:sheet.save(f,format='PNG',optimize=False)
    all_assets[path.relative_to(s.OUT).as_posix()]=s.sha(path)
    matrix={'scenarios':scenarios,'execution_order_scenario_ids':order,'order_rule':'fixed SHA rank within representation, round-robin Multi/Story/Video; no response observed',
      'run_order_sha256':hashlib.sha256(s.canonical(order)).hexdigest(),'renderer_sha256':s.sha(__file__),
      'media_assets_sha256':all_assets,'model_visible_intended_metadata':False,'old_assets_read':False,'new_source_frames':64,
      'processor_budget':{'max_pixels':200704,'min_pixels':3136,'storyboard':[1440,906],'temporal_patch_size':2,'video_do_sample_frames':False},
      'classification':'engineering fixture intent only; no physical event GT','lock_sequence':['source_audit','matrix_defined','CPU_render','technical_checks','fixture_lock','V1D_authoring_later']}
    s.save('V1D_SYNTHETIC_FIXTURE_MANIFEST.json',matrix)
    s.save('FIXTURE_LOCK_RECEIPT.json',{'fixture_manifest_sha256':s.sha(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json'),
      'renderer_sha256':s.sha(__file__),'order_sha256':matrix['run_order_sha256'],'created_at_unix':s.time.time(),
      'candidate_exists_at_lock':False,'model_generations':0,'kind':'PROSPECTIVE_SYNTHETIC_FIXTURE_LOCK_NOT_PROTOCOL_FREEZE'})
    for p in [s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json',s.OUT/'FIXTURE_LOCK_RECEIPT.json',s.OUT/'renderer.py',*(s.OUT/'media').rglob('*.png')]:p.chmod(0o444)
    print('FIXTURES_LOCKED',s.sha(s.OUT/'FIXTURE_LOCK_RECEIPT.json'),flush=True)

if __name__=='__main__':generate()
