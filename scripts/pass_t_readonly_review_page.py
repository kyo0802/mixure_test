"""Loopback-only, allowlisted viewer for two authorized human review windows."""
import hashlib
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'artifacts/pass_t/phase2a/v2'
manifest = json.loads((OUT/'manifest.json').read_bytes())
WANTED = {'PT2A_eb60192e6986cb4f': ('test5 W05', [342,389,449]),
          'PT2A_c58b4df88a2f6801': ('test7 W05', [380,404,445])}
windows, media = [], {}
for entry in manifest['items']:
    if entry['annotation_item_id'] not in WANTED: continue
    raw = (OUT/entry['item_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry['item_sha256']
    item = json.loads(raw)
    title, jumps = WANTED[entry['annotation_item_id']]
    record = {'title':title,'jumps':jumps,'target':item['selected_local_candidate_id'],'frames':[],'references':[]}
    for kind in ('frames','references'):
        for f in item['visual'][kind]:
            path = (ROOT/f['image_path']).resolve()
            assert path.is_relative_to(ROOT) and hashlib.sha256(path.read_bytes()).hexdigest() == f['sha256']
            url = '/media/' + str(len(media))
            media[url] = path
            record[kind].append({'url':url,'id':f.get('frame_id',f.get('reference_id')),
                                'index':f['source_frame_index'],'pts':f['source_timestamp_s']})
    windows.append(record)

HTML = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Pass T 人工影格複核</title>
<style>body{font:17px system-ui;background:#101820;color:#eef2f7;margin:24px}button,select{font:inherit;padding:9px;margin:4px;cursor:pointer}input{width:95%}#frame{max-width:100%;max-height:72vh;display:block;margin:auto}a{color:#8fd6ff}.panel{background:#203040;padding:16px;border-radius:10px;margin:14px 0}.refs img{max-width:260px;max-height:210px;margin:8px}small{color:#b9c8d8}</style>
<h1>Pass T：test5 / test7 人工影格複核</h1>
<p>唯讀檢視，不會儲存或修改任何標註。請先確認目標，再逐格檢查拿起的物理轉換；消失本身不能證明 PICKUP。</p>
<select id="window"></select><span id="target"></span>
<div class="panel"><button id="prev">← 上一格</button><button id="play">播放（約 5 fps）</button><button id="next">下一格 →</button><span id="jumps"></span>
<p id="label"></p><input id="slider" type="range" min="0" value="0"><p><a id="original" target="_blank">開啟此張原尺寸影格</a> <small>可用鍵盤左右鍵逐格查看。圖片為原始影格，沒有新增追蹤框。</small></p>
<img id="frame" alt="授權視窗影格"></div>
<details class="panel"><summary>目標參考圖（窗前參考，只供辨識，不能作事件時間證據）</summary><div id="refs" class="refs"></div></details>
<div class="panel"><b>看完後回覆：</b><p>test5 W05：支持 PICKUP／證據不足／有矛盾證據；影格編號與看到的物理變化。</p><p>test7 W05：支持 PICKUP／證據不足／有矛盾證據；影格編號與看到的物理變化。</p><small>本頁只是複核入口，不代表整個事件清單已獲完整性認證。</small></div>
<script>const windows=DATA;let w, timer=null;const $=id=>document.getElementById(id);
function stop(){clearInterval(timer);timer=null;$('play').textContent='播放（約 5 fps）'}
function show(){const i=Number($('slider').value),f=w.frames[i];$('frame').src=f.url;$('original').href=f.url;$('label').textContent=`${w.title} ｜ ${f.id} ｜ Native PTS ${f.pts.toFixed(3)} s ｜ ${i+1} / ${w.frames.length}`}
function move(d){$('slider').value=Math.max(0,Math.min(w.frames.length-1,Number($('slider').value)+d));show()}
function select(){stop();w=windows[Number($('window').value)];$('target').textContent=' 當窗目標 local candidate '+w.target+'（不是全域身分）';$('slider').max=w.frames.length-1;$('slider').value=0;$('jumps').replaceChildren();w.jumps.forEach((n,i)=>{let b=document.createElement('button');b.textContent=['BEFORE','TRANSITION','AFTER'][i]+' S'+String(n).padStart(6,'0');b.onclick=()=>{stop();$('slider').value=w.frames.findIndex(f=>f.index===n);show()};$('jumps').append(b)});$('refs').replaceChildren();w.references.forEach(f=>{let a=document.createElement('a');a.href=f.url;a.target='_blank';let im=document.createElement('img');im.src=f.url;im.alt=f.id;a.append(im);$('refs').append(a)});show()}
windows.forEach((w,i)=>{let o=document.createElement('option');o.value=i;o.textContent=w.title;$('window').append(o)});$('window').onchange=select;$('slider').oninput=()=>{stop();show()};$('prev').onclick=()=>{stop();move(-1)};$('next').onclick=()=>{stop();move(1)};$('play').onclick=()=>{if(timer){stop();return}if(Number($('slider').value)===w.frames.length-1)$('slider').value=0;$('play').textContent='暫停';timer=setInterval(()=>{move(1);if(Number($('slider').value)===w.frames.length-1)stop()},200)};document.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();stop();move(e.key==='ArrowRight'?1:-1)}};select();</script></html>'''.replace('DATA',json.dumps(windows,ensure_ascii=False)).encode('utf-8')

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/','/review'):
            raw,kind = HTML,'text/html; charset=utf-8'
        elif self.path in media:
            raw,kind = media[self.path].read_bytes(),'image/png'
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
        self.end_headers(); self.wfile.write(raw)

if __name__ == '__main__':
    print('Read-only review: http://127.0.0.1:8512/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8512),Handler).serve_forever()
