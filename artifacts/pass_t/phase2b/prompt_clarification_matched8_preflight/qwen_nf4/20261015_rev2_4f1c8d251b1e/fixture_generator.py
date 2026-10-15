"""Deterministic CPU-rendered desk interactions, not physical-event ground truth."""
import core
import math,random
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

W,H=1280,720
def render(seed,sequence,frame):
    rng=random.Random(seed)
    # Neutral furnished scene, textured wall/desk, stationary mug and plant.
    yy,xx=np.mgrid[0:H,0:W]
    grain=np.random.default_rng(seed).integers(-3,4,(H,W,1))
    rgb=np.zeros((H,W,3),dtype=np.int16)
    for c,base in enumerate([221,219,213]):rgb[:,:,c]=base-(yy*14//H)
    desk=yy>360
    for c,base in enumerate([156,119,83]):rgb[:,:,c][desk]=base+((xx//7+yy//19)%5)[desk]
    rgb=np.clip(rgb+grain,0,255).astype('uint8');im=Image.fromarray(rgb)
    d=ImageDraw.Draw(im)
    d.rectangle((0,354,W,366),fill=(100,78,58))
    d.rounded_rectangle((1030,435,1112,534),radius=15,fill=(236,232,216),outline=(146,141,127),width=3)
    d.ellipse((1028,425,1115,448),fill=(88,69,49),outline=(225,220,206),width=8)
    d.arc((1088,447,1154,516),270,90,fill=(225,220,206),width=10)
    d.polygon([(100,468),(178,468),(169,531),(111,531)],fill=(146,109,86))
    for k in range(6):
        x=139+int(24*math.sin(k));d.line((139,475,x,390-k*10),fill=(72,98,53),width=4)
        d.ellipse((x-21,388-k*10,x+15,408-k*10),fill=(72+4*k,103+5*k,59))
    # Poses are authored once before the candidate prompt exists.
    poses={
      'steady_supported':[(0,0,False)]*8,
      'steady_held':[(35,-110,True)]*8,
      'lift':[(0,0,False),(0,0,True),(0,-15,True),(8,-65,True),(25,-125,True),(50,-150,True),(65,-155,True),(80,-155,True)],
      'lower':[(65,-155,True),(50,-140,True),(25,-90,True),(7,-30,True),(0,0,True),(0,0,True),(0,0,False),(0,0,False)],
      'lift_lower':[(0,0,False),(0,0,True),(5,-45,True),(35,-145,True),(40,-145,True),(15,-65,True),(0,0,True),(0,0,False)],
      'lower_lift':[(30,-125,True),(10,-55,True),(0,0,True),(0,0,False),(0,0,True),(15,-75,True),(40,-145,True),(60,-150,True)]}
    dx,dy,hand=poses[sequence][frame]
    x=510+dx+rng.randint(-22,22);y=500+dy
    shadow=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(shadow)
    alpha=max(35,90+dy//3);sd.ellipse((x-30,513,x+168,559),fill=(15,12,8,alpha))
    im=Image.alpha_composite(im.convert('RGBA'),shadow.filter(ImageFilter.GaussianBlur(10))).convert('RGB');d=ImageDraw.Draw(im)
    casing=[rng.randint(22,55),rng.randint(25,60),rng.randint(25,60)]
    d.rounded_rectangle((x,y-56,x+134,y+18),radius=12,fill=tuple(casing),outline=(14,15,17),width=4)
    d.rounded_rectangle((x+9,y-48,x+125,y+9),radius=7,fill=(55,70,79))
    d.polygon([(x+15,y-43),(x+88,y-43),(x+115,y+3),(x+73,y+3)],fill=(70,87,96))
    d.ellipse((x+60,y-48,x+69,y-40),fill=(20,23,25))
    if hand:
        skin=(198,151,118)
        d.polygon([(x+80,y-15),(x+250,y-16),(x+350,y+100),(x+302,y+149),(x+130,y+50)],fill=skin)
        for k in range(4):
            d.rounded_rectangle((x+95,y-44+k*16,x+195-k*8,y-25+k*16),radius=10,fill=skin,outline=(162,113,87),width=2)
        d.rounded_rectangle((x+72,y+2,x+133,y+23),radius=10,fill=(206,159,125),outline=(162,113,87),width=2)
        for k in range(3):d.line((x+165+k*20,y+24,x+185+k*20,y+40),fill=(172,126,97),width=2)
    return im

SCENARIOS=[('steady_supported',0,18421),('steady_held',0,39017),('lift',1,57139),('lower',1,62843),('lift_lower',2,73591),('lower_lift',2,84629),('steady_supported','WARMUP',95713)]
