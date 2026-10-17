/* Controller integration with DOM test doubles. NOT a browser/playback test. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),{webcrypto}=require('node:crypto');
const tool=path.resolve(__dirname,'../tools/findmind-gt-annotator'),html=fs.readFileSync(path.join(tool,'index.html'),'utf8'),M=JSON.parse(fs.readFileSync(path.join(tool,'manifest.json'))),S=JSON.parse(fs.readFileSync(path.join(tool,'schema.json'))),C=require(path.join(tool,'contract.js'));
function boot(storage=new Map(),storageBroken=false,missingManifest=false){
 const nodes=new Map(),downloads=[],blobs=new Map();let document;
 class Element {
  constructor(tag,id=''){this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.listeners={};this._value=null;this.defaultValue='';this._text='';this.checked=false;this.defaultChecked=false;this.hidden=false;this.className='';this.style={};this.parent=null;if(id)nodes.set(id,this);}
  append(...xs){for(const x of xs){this.children.push(x);x.parent=this;}}
  replaceChildren(...xs){this.children=[];this.append(...xs);if(this.tagName==='SELECT')this._value=null;}
  get options(){return this.children.filter(x=>x.tagName==='OPTION');}
  get value(){if(this.tagName==='SELECT'){const o=this.options.find(x=>x.value===this._value)||this.options[0];return o?o.value:'';}return this._value===null?(this.tagName==='OPTION'?this.textContent:''):this._value;}
  set value(x){this._value=String(x);}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  set textContent(x){this._text=String(x);this.children=[];}
  addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
  emit(type,event={}){const e={preventDefault(){},target:this,...event};for(const f of this.listeners[type]||[])f(e);if(this['on'+type])return this['on'+type](e);}
  click(){if(this.tagName==='A'&&this.download)downloads.push({filename:this.download,blob:blobs.get(this.href)});return this.emit('click');}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}
  setAttribute(k,v){this[k]=v;}
  focus(){document.activeElement=this;}
  pause(){this.paused=true;}
  play(){this.paused=false;return Promise.resolve();}
  querySelectorAll(selector){const all=[];function walk(n){for(const x of n.children){all.push(x);walk(x);}}walk(this);if(selector==='input:checked')return all.filter(x=>x.tagName==='INPUT'&&x.checked);return [];}
  reset(){const form=html.match(new RegExp('<form[^>]*id="'+this.id+'"[^>]*>([\\s\\S]*?)</form>'))?.[1]||'';for(const match of form.matchAll(/\bid="([^"]+)"/g)){const n=nodes.get(match[1]);if(n){n.value=n.defaultValue;n.checked=n.defaultChecked;if(n.tagName==='SELECT')n._value=null;}}}
 }
 for(const m of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="[^"]+"[^>]*)>/g)){
  const attrs=m[2],id=attrs.match(/\bid="([^"]+)"/)[1],n=new Element(m[1],id);n.className=attrs.match(/\bclass="([^"]*)"/)?.[1]||'';n.defaultValue=attrs.match(/\bvalue="([^"]*)"/)?.[1]||'';n.value=n.defaultValue;n.checked=n.defaultChecked=/\bchecked\b/.test(attrs);n.hidden=/\bhidden\b/.test(attrs);
  if(n.tagName==='SELECT'){n._value=null;const body=html.slice(m.index).match(/^[\s\S]*?<\/select>/)?.[0]||'';for(const opt of body.matchAll(/<option([^>]*)>([^<]*)/g)){const o=new Element('option');o.textContent=opt[2];o.value=opt[1].match(/value="([^"]*)"/)?.[1]||opt[2];n.append(o);if(/\bselected\b/.test(opt[1]))n.value=o.value;}}
 }
 const body=new Element('body');document={body,activeElement:body,createElement:t=>new Element(t),createTextNode:s=>{const n=new Element('#text');n.textContent=s;return n;},getElementById:id=>{if(nodes.has(id))return nodes.get(id);for(const n of nodes.values()){const scan=x=>x.id===id?x:x.children.map(scan).find(Boolean);const found=scan(n);if(found)return found;}return null;},querySelectorAll:s=>[...nodes.values()].filter(n=>s.startsWith('.')?n.className.split(' ').includes(s.slice(1)):s==='input[type=number]'?n.tagName==='INPUT'&&html.includes('id="'+n.id+'" type="number"'):false),addEventListener(){}};
 const player=nodes.get('player');player.currentTime=0;player.paused=true;player.playbackRate=1;
 const localStorage={get length(){return storage.size;},key:i=>[...storage.keys()][i],getItem:k=>storage.get(k)||null,setItem:(k,v)=>{if(storageBroken)throw Error('TEST_QUOTA_FAILURE');storage.set(k,v);},removeItem:k=>storage.delete(k)};
 const window={FindMindGT:C,FINDMIND_MANIFEST:missingManifest?undefined:M,FINDMIND_SCHEMA:S,addEventListener(){}};
 const context={window,document,localStorage,Blob,URL:{createObjectURL:blob=>{const key='blob:test:'+blobs.size;blobs.set(key,blob);return key;},revokeObjectURL(){}},crypto:webcrypto,confirm:()=>true,setTimeout:()=>1,console};
 vm.runInNewContext(fs.readFileSync(path.join(tool,'app.js'),'utf8'),context,{filename:'app.js'});
 const $=id=>document.getElementById(id);
 function loaded(id='test1'){const m=M.videos.find(x=>x.video_id===id);player.duration=m.source_duration_s;player.videoWidth=m.width;player.videoHeight=m.height;player.emit('loadedmetadata');}
 function start(name='ISOLATED_UI_TEST_A'){$('reviewer').value=name;$('assignment').value='SOFTWARE TEST ONLY; NOT HUMAN GT';$('session-form').emit('submit');loaded();}
 async function exported(){ $('export').click();assert.ok(downloads.length,'must initiate a real Blob download in controller');return JSON.parse(await downloads.at(-1).blob.text()); }
 function findButton(node,label){for(const n of node.children){if(n.tagName==='BUTTON'&&n.textContent===label)return n;const q=findButton(n,label);if(q)return q;}return null;}
 return {$,start,loaded,exported,storage,player,downloads,findButton};
}
(async()=>{
 let passed=0;function ok(name,fn){fn();passed++;console.log('PASS '+name);}
 const ui=boot(),$=ui.$;ui.start();
 ok('session start and nine navigation entries',()=>assert.equal($('video-list').children.length,9,$('message').textContent));
 $('play').click();ok('play/pause controller',()=>{assert.equal(ui.player.paused,false);$('play').click();assert.equal(ui.player.paused,true);});
 $('seek').value='1.5';$('seek').emit('input');ok('seek sets source-time request',()=>assert.equal(ui.player.currentTime,1.5));
 ui.player.currentTime=1;$('set-start').click();ui.player.currentTime=2;$('set-end').click();$('event-category').value='TEST_OBJECT';$('event-instance').value='TEST_1';$('before-state').value='ON_SURFACE';$('after-state').value='HELD_BY_PERSON';$('before-visibility').value='VISIBLE';$('after-visibility').value='VISIBLE';$('event-certainty').value='CONFIRMED';$('event-identity').value='CERTAIN';ui.player.currentTime=.5;$('add-before').click();ui.player.currentTime=2.5;$('add-after').click();$('event-notes').value='SYNTHETIC SOFTWARE TEST ONLY';$('event-form').emit('submit');
 let first=await ui.exported(),eid=first.videos[0].events[0]?.event_id;
 ok('create event through actual controller handlers',()=>{assert.equal(first.videos[0].events.length,1);assert.equal(first.videos[0].events[0].start_s,1);assert.equal(first.videos[0].events[0].end_s,2);});
 ui.findButton($('event-list'),'編輯').click();$('event-end').value='2.2';$('event-notes').value='EDITED TEST LABEL';$('event-form').emit('submit');let edited=await ui.exported();
 ok('edit preserves event identity',()=>{assert.equal(edited.videos[0].events.length,1);assert.equal(edited.videos[0].events[0].event_id,eid);assert.equal(edited.videos[0].events[0].end_s,2.2);});
 $('tab-state').click();$('state-category').value='TEST_OBJECT';$('state-instance').value='TEST_1';$('state-time').value='.5';$('physical-state').value='ON_SURFACE';$('state-visibility').value='VISIBLE';$('state-certainty').value='CONFIRMED';$('state-identity').value='CERTAIN';$('state-form').emit('submit');let states=await ui.exported();
 ok('state creation does not invent verified frame index',()=>{assert.equal(states.videos[0].states.length,1);assert.equal(states.videos[0].states[0].source_frame_index,null);});
 $('tab-coverage').click();$('interval-start').value='0';$('interval-end').value='3';$('interval-form').emit('submit');$('uncertainty-start').value='3';$('uncertainty-end').value='4';$('uncertainty-reason').value='SYNTHETIC TEST GAP';$('uncertainty-form').emit('submit');$('review-status').value='PARTIALLY_REVIEWED';$('coverage-form').emit('submit');let partial=await ui.exported();
 ok('partial coverage and uncertainty persist separately',()=>{assert.equal(partial.videos[0].reviewed_intervals.length,1);assert.equal(partial.videos[0].uncertain_intervals.length,1);assert.equal(partial.videos[0].event_list_exhaustiveness,'NOT_ATTESTED');});
 $('full-interval').click();$('review-status').value='EXHAUSTIVELY_REVIEWED';C.attestations.forEach(k=>$('attest-'+k).checked=true);$('coverage-form').emit('submit');let full=await ui.exported();
 ok('obscured gap blocks scientific exhaustiveness despite reviewed timeline',()=>{assert.equal(full.videos[0].review_status,'EXHAUSTIVELY_REVIEWED');assert.equal(full.videos[0].event_list_exhaustiveness,'NOT_ATTESTED');});
 const reloaded=boot(ui.storage);reloaded.$('resume').click();reloaded.loaded();let resumed=await reloaded.exported();
 ok('close/reopen simulation restores local session',()=>{assert.equal(resumed.session_id,full.session_id);assert.deepEqual(resumed.videos,full.videos);});
 const test2=reloaded.$('video-list').children.find(x=>x.textContent.startsWith('test2'));test2.click();reloaded.loaded('test2');reloaded.$('video-list').children.find(x=>x.textContent.startsWith('test1')).click();reloaded.loaded();
 ok('switching video preserves saved records',()=>assert.ok(reloaded.$('event-list').textContent.includes('TEST_OBJECT')));
 const before=await reloaded.exported(),bad=C.clone(before);bad.dataset_version='wrong';await reloaded.$('import-file').emit('change',{target:{files:[{size:100,text:async()=>JSON.stringify(bad)}]}});const after=await reloaded.exported();
 ok('invalid import leaves annotations unchanged',()=>assert.deepEqual(after.videos,before.videos));
 reloaded.findButton(reloaded.$('event-list'),'刪除').click();reloaded.findButton(reloaded.$('state-list'),'刪除').click();const deleted=await reloaded.exported();
 ok('event/state deletion invalidates earlier exhaustive attestations',()=>{assert.equal(deleted.videos[0].events.length,0);assert.equal(deleted.videos[0].states.length,0);assert.equal(deleted.videos[0].review_status,'IN_PROGRESS');assert.equal(deleted.videos[0].event_list_exhaustiveness,'NOT_ATTESTED');});
 const imported=boot();await imported.$('import-file').emit('change',{target:{files:[{size:JSON.stringify(before).length,text:async()=>JSON.stringify(before)}]}});imported.loaded();let roundtrip=await imported.exported();
 ok('downloaded JSON re-import restores reviewer/session/events/state/coverage',()=>{assert.equal(roundtrip.reviewer_id,before.reviewer_id);assert.equal(roundtrip.session_id,before.session_id);assert.deepEqual(roundtrip.videos,before.videos);});
 imported.$('new-session').click();imported.start('ISOLATED_UI_TEST_B');const independent=await imported.exported();
 ok('second reviewer does not inherit first reviewer labels',()=>{assert.notEqual(independent.session_id,before.session_id);assert.equal(independent.videos[0].events.length,0);});
 const noStorage=boot(new Map(),true);noStorage.start('ISOLATED_UI_TEST_STORAGE');const portable=await noStorage.exported();
 ok('local storage failure is visible and Blob export still works',()=>{assert.equal(noStorage.$('storage-warning').hidden,false);assert.equal(portable.reviewer_id,'ISOLATED_UI_TEST_STORAGE');});
 const missing=boot(new Map(),false,true);ok('incomplete extraction displays a clear startup error',()=>assert.ok(missing.$('message').textContent.includes('完整')));
 console.log('RESULT '+passed+' DOM-double controller checks passed. Not a Chromium/file:// or actual video playback test. Test labels stayed in memory.');
})().catch(e=>{console.error(e);process.exitCode=1;});
