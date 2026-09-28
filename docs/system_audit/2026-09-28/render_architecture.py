"""Render an engineering diagram of the audited system (no model inference)."""
from pathlib import Path
import os
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / '.venv/Lib/site-packages'))
os.environ['MPLCONFIGDIR'] = str(HERE/'runtime/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties

font = FontProperties(fname=r'C:\Windows\Fonts\msjh.ttc')
plt.rcParams['svg.fonttype'] = 'path'
fig, ax = plt.subplots(figsize=(18, 12), dpi=150)
fig.patch.set_facecolor('#f4f7fb')
ax.set(xlim=(0,2400), ylim=(1600,0))
ax.axis('off')
fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
colors = {'done':('#e5f3ed','#177458'), 'partial':('#fff0da','#b76c0a'), 'side':('#e9edf5','#55647d')}

def txt(x,y,s,size=17,color='#203348',weight='normal',ha='left'):
    ax.text(x,y,s,fontproperties=font,fontsize=size,color=color,weight=weight,ha=ha,va='top',linespacing=1.55)

def box(x,y,w,h,title,body,kind='done'):
    fill, edge = colors[kind]
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=16',facecolor=fill,edgecolor=edge,lw=1.4))
    ax.add_patch(FancyBboxPatch((x+20,y+23),7,35,boxstyle='round,pad=0,rounding_size=2',facecolor=edge,edgecolor=edge))
    txt(x+43,y+20,title,19,edge,'bold')
    txt(x+27,y+79,body,16)

def arrow(points,color='#6b7f94',dash=False):
    for a,b in zip(points[:-2],points[1:-1]):
        ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=1.8,ls='--' if dash else '-')
    ax.add_patch(FancyArrowPatch(points[-2],points[-1],arrowstyle='-|>',mutation_scale=18,lw=1.8,color=color,linestyle='--' if dash else '-'))

txt(65,35,'FindMind｜實際資料流與完成度',30,weight='bold')
txt(68,103,'V2.9.1 全系統稽核 · 2026-09-28 · 離線研究原型',17,'#587085')
for x,kind,label in [(1320,'done','已接通／有案例驗證'),(1710,'partial','部分完成／待修正'),(2090,'side','實驗／未建置')]:
    ax.scatter([x],[78],s=150,color=colors[kind][1]);txt(x+24,61,label,14)

xs=[65,645,1225,1805]
box(xs[0],205,530,220,'01　RGB 影片輸入','test1.mp4 – test9.mp4\n完整解碼、5 FPS 基礎抽樣\nmetadata／frame time／內容 hash')
box(xs[1],205,530,220,'02　感知與局部身份','YOLO11s ＋ 分類別 ByteTrack\ntrack 品質／短距離關聯\n持續保留電話 detections')
box(xs[2],205,530,220,'03　目標與候選證據','綁定 phone_01 → SAM2.1\n候選 SAM ＋ MobileNetV3 外觀\n可信 bank／多視角／來源 ID','partial')
box(xs[3],205,530,220,'04　融合與 Identity Guard','EntityRegistry：YOLO／SAM\nCONFIRMED / PROVISIONAL\nAMBIGUOUS；只有確認可授權','partial')
for x in xs[:-1]: arrow([(x+530,310),(x+577,310)])

txt(65,496,'記憶與搜尋主線：直接可信觀測＋事件增補',19,'#203348','bold')
box(xs[3],595,530,220,'05　事件＋密集視窗','LOSS／RECONFIRM／PUTDOWN\nV2.9／V2.9.1 短窗重檢\n舊 cache 範圍與 mask 路徑待修','partial')
box(xs[2],595,530,220,'06　錨點＋可觀察事實','persistent／event-local anchors\nQwen2.5-VL-3B ＋ physical gate\n新分支只到 CANDIDATE','partial')
box(xs[1],595,530,220,'07　目標空間時間記憶','V2.8 local graph／episodes\nlifetime／snapshots／狀態歷史\n身份、時間、視圖一致性待修','partial')
box(xs[0],595,530,220,'08　搜尋與稽核輸出','規則排序／JSON／圖表／影片\n199 個候選；0 真實物理升格\n候選數不等於尋物成功率','partial')
arrow([(2070,425),(2070,592)])
for x in xs[1:]:arrow([(x,700),(x-48,700)])
arrow([(1990,425),(1990,552),(910,552),(910,592)],'#177458')
txt(1100,514,'可信身份觀測直接進 memory',13,'#177458')
txt(590,847,'←　新事件產生的未確認候選，也追加至 memory / search',16,'#98600d')

txt(65,937,'仍須接通的部分與獨立分支',19,'#203348','bold')
box(65,1000,720,270,'實際執行路徑','test1/2：從 raw 影片跑上游，再進 V2.9.1\ntest3–9：重用 V2.5/2.6/2.8/2.9 輸出\n目前是版本模組串接；不是統一最新 runner\nraw 分支還缺 V2.9 placement detector','side')
box(840,1000,720,270,'重尋與確認後回饋：尚未閉合','rediscovery 目前整理既有 candidate stream\n確認 → SAM reinit → guard → memory 未完整\n再次 LOST 的恢復需要完整 state machine\n不能把 SAM local ID 直接當作 phone_01','partial')
box(1615,1000,720,270,'模型實驗與產品層','SAM3/3.1：獨立實驗；主線保留 SAM2.1\nSAM3 concept：只有候選發現價值的證據\nUI／API／多目標／跨影片長期記憶未完成\n即時攝影機／世界座標與導航尚未建置','side')

ax.add_patch(FancyBboxPatch((65,1340),2270,170,boxstyle='round,pad=0,rounding_size=16',facecolor='#fff',edgecolor='#d6dee8',lw=1.2))
txt(91,1360,'最優先修正',19,'#a43c36','bold')
txt(91,1415,'身份誤標：7 次 propagated → MATCHED   │   173 筆新記憶時間為 0 秒   │   7 個 cache 視窗不完整   │   VLM 對準目標不足',15)
txt(68,1550,'資料來源：現行程式＋V2.9.1 frozen artifacts；本次僅盤點與測試，未重新執行模型。',13,'#587085')
fig.savefig(HERE/'architecture.png',dpi=150)
fig.savefig(HERE/'architecture.svg')
plt.close(fig)

md=(HERE/'FINDMIND_SYSTEM_AUDIT.md').read_text(encoding='utf-8')
mermaid=md.split('```mermaid\n',1)[1].split('```',1)[0]
(HERE/'architecture.mmd').write_text(mermaid,encoding='utf-8')
print('Rendered architecture.png / architecture.svg / architecture.mmd')
