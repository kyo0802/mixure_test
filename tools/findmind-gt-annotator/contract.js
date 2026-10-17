/* Pure annotation data contract; classic browser script and Node test import. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FindMindGT = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const attestations = ['entire_timeline_reviewed','all_pickup_placement_annotated','all_uncertainty_recorded','identity_not_guessed','no_unobservable_gap','target_association_resolved'];
  const now = () => new Date().toISOString();
  const clone = x => JSON.parse(JSON.stringify(x));
  function id(prefix) {
    const uuid = globalThis.crypto && globalThis.crypto.randomUUID ? globalThis.crypto.randomUUID() : Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)+'-'+Math.random().toString(36).slice(2);
    return prefix+'_'+uuid;
  }
  function strictParse(text) {
    if (text.length > 20*1024*1024) throw Error('JSON 超過 20 MB');
    text=text.replace(/^\uFEFF/,'');let pos=0,nodes=0;
    const ws=()=>{while(/[ \t\r\n]/.test(text[pos]||'') && pos<text.length)pos++;};
    function string() {
      const start=pos++;let escaped=false;
      while(pos<text.length){let c=text[pos++];if(c==='"'&&!escaped)return JSON.parse(text.slice(start,pos));if(c==='\\'&&!escaped)escaped=true;else escaped=false;}
      throw Error('字串未結束');
    }
    function value(depth) {
      if(depth>40 || ++nodes>300000)throw Error('JSON 結構過大');ws();let c=text[pos];
      if(c==='"')return string();
      if(c==='{') {pos++;ws();const result=Object.create(null),keys=new Set();if(text[pos]==='}'){pos++;return result;}
        for(;;){ws();if(text[pos]!=='"')throw Error('JSON 欄位名稱錯誤');const k=string();if(keys.has(k))throw Error('重複 JSON 欄位：'+k);keys.add(k);ws();if(text[pos++]!==':')throw Error('缺少冒號');result[k]=value(depth+1);ws();const sep=text[pos++];if(sep==='}')return result;if(sep!==',')throw Error('JSON 物件分隔錯誤');}}
      if(c==='['){pos++;ws();const a=[];if(text[pos]===']'){pos++;return a;}for(;;){a.push(value(depth+1));ws();let sep=text[pos++];if(sep===']')return a;if(sep!==',')throw Error('JSON 陣列分隔錯誤');}}
      for(const [word,v] of [['true',true],['false',false],['null',null]])if(text.startsWith(word,pos)){pos+=word.length;return v;}
      const match=text.slice(pos).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
      if(!match)throw Error('JSON 值錯誤，位置 '+pos);pos+=match[0].length;const n=Number(match[0]);if(!Number.isFinite(n))throw Error('不可使用非有限數字');return n;
    }
    const result=value(0);ws();if(pos!==text.length)throw Error('JSON 後有多餘內容');return result;
  }
  function structural(value,schema) {
    const errors=[];
    function visit(x,rule,path) {
      if(rule.$ref)rule=schema.definitions[rule.$ref.split('/').pop()];
      const types=Array.isArray(rule.type)?rule.type:rule.type?[rule.type]:[];
      const matches=t=>t==='null'?x===null:t==='array'?Array.isArray(x):t==='object'?x!==null&&typeof x==='object'&&!Array.isArray(x):t==='integer'?Number.isInteger(x):t==='number'?typeof x==='number'&&Number.isFinite(x):typeof x===t;
      if(types.length&&!types.some(matches)){errors.push(path+'：欄位型別錯誤');return;}
      if(Object.prototype.hasOwnProperty.call(rule,'const')&&x!==rule.const)errors.push(path+'：版本／固定值錯誤');
      if(rule.enum&&!rule.enum.includes(x))errors.push(path+'：不支援的選項');
      if(x!==null&&typeof x==='object'&&!Array.isArray(x)) {
        for(const k of rule.required||[])if(!Object.prototype.hasOwnProperty.call(x,k))errors.push(path+'/'+k+'：缺少必填欄位');
        for(const k of Object.keys(x)){if(!Object.prototype.hasOwnProperty.call(rule.properties||{},k)){if(rule.additionalProperties===false)errors.push(path+'/'+k+'：不支援的欄位');}else visit(x[k],rule.properties[k],path+'/'+k);}
      }
      if(Array.isArray(x)){if(x.length<(rule.minItems||0)||x.length>(rule.maxItems===undefined?Infinity:rule.maxItems))errors.push(path+'：筆數錯誤');x.forEach((a,i)=>visit(a,rule.items||{},path+'/'+i));}
      if(typeof x==='string'){if(x.length<(rule.minLength||0)||x.length>(rule.maxLength===undefined?Infinity:rule.maxLength))errors.push(path+'：字數錯誤');if(rule.pattern&&!new RegExp(rule.pattern).test(x))errors.push(path+'：欄位格式錯誤');}
      if(typeof x==='number'&&x<(rule.minimum===undefined?-Infinity:rule.minimum))errors.push(path+'：數值過小');
    }
    visit(value,schema,'$');return errors;
  }
  function coversFull(intervals,duration) {
    let end=0;for(const i of [...intervals].sort((a,b)=>a.start_s-b.start_s)){if(i.start_s>end+1e-6)return false;end=Math.max(end,i.end_s);}return end>=duration-1e-6;
  }
  function exhaustiveness(v) {
    if(v.review_status==='NOT_STARTED')return 'UNKNOWN';
    const full=v.review_status==='EXHAUSTIVELY_REVIEWED'&&attestations.every(k=>v.coverage_attestations[k])&&coversFull(v.reviewed_intervals,v.source_duration_s);
    const hidden=v.uncertain_intervals.some(x=>x.could_conceal_event||x.identity_uncertain);
    const unresolved=v.events.some(e=>['PICKUP','PLACEMENT'].includes(e.type)&&(e.evidence_certainty!=='CONFIRMED'||e.target_identity_certainty!=='CERTAIN'||e.local_instance_id.trim().toUpperCase()==='UNKNOWN'));
    return full&&!hidden&&!unresolved?'EXHAUSTIVE_ATTESTED':'NOT_ATTESTED';
  }
  function nearest(meta,t) {
    const frames=meta.frame_timeline;let lo=0,hi=frames.length-1;while(lo<hi){const mid=Math.floor((lo+hi)/2);if(frames[mid].source_time_s<t)lo=mid+1;else hi=mid;}
    return lo&&Math.abs(frames[lo-1].source_time_s-t)<=Math.abs(frames[lo].source_time_s-t)?lo-1:lo;
  }
  function validate(bundle,manifest,schema) {
    let errors=structural(bundle,schema);if(errors.length)return errors;
    for(const k of ['dataset_id','dataset_version','dataset_manifest_sha256'])if(bundle[k]!==manifest[k])errors.push('資料集身分／版本不符：'+k);
    const seenVideos=new Set(),seenIDs=new Set(),expected=new Map(manifest.videos.map(v=>[v.video_id,v]));
    for(const v of bundle.videos){const vid=v.video_id; if(seenVideos.has(vid))errors.push('重複影片：'+vid);seenVideos.add(vid);const meta=expected.get(vid);if(!meta){errors.push('未知影片：'+vid);continue;}
      if(v.source_sha256!==meta.source_sha256||Math.abs(v.source_duration_s-meta.source_duration_s)>1e-8)errors.push(vid+'：原始影片身分／時長不符');
      const time=t=>{if(t<0||t>meta.source_duration_s+1e-8)errors.push(vid+'：時間超出影片範圍');};
      for(const [key,idKey] of [['events','event_id'],['states','state_id'],['reviewed_intervals','interval_id'],['uncertain_intervals','uncertainty_id']])for(const item of v[key]){
        if(seenIDs.has(item[idKey]))errors.push('重複標註 ID：'+item[idKey]);seenIDs.add(item[idKey]);
        if(key==='states'){time(item.source_time_s);if(item.source_frame_index!==null)errors.push(vid+'：HTML5 不可宣稱已驗證 source frame index');if(item.nearest_source_frame_index!==null&&(item.nearest_source_frame_index<0||item.nearest_source_frame_index>=meta.frame_count))errors.push(vid+'：鄰近影格索引錯誤');if(item.evidence_certainty==='CONFIRMED'&&['ON_SURFACE','HELD_BY_PERSON'].includes(item.physical_state)&&['NOT_VISIBLE','UNCERTAIN'].includes(item.visibility))errors.push(vid+'：不可見狀態不能宣稱確定的直接支持');}
        else{time(item.start_s);time(item.end_s);if(item.start_s>item.end_s)errors.push(vid+'：開始時間不得大於結束時間');}
        if(key==='events'){const bf=item.before_evidence_times_s,af=item.after_evidence_times_s;[...bf,...af].forEach(time);if(bf.length&&af.length&&Math.max(...bf)>Math.min(...af))errors.push(vid+'：before/after 證據時間顛倒');if(['PICKUP','PLACEMENT'].includes(item.type)&&item.evidence_certainty==='CONFIRMED'){const pair=item.type==='PICKUP'?['ON_SURFACE','HELD_BY_PERSON']:['HELD_BY_PERSON','ON_SURFACE'];if(item.before_state!==pair[0]||item.after_state!==pair[1]||!bf.length||!af.length)errors.push(vid+'：確定事件需正確前後狀態及兩側證據時間');if(['NOT_VISIBLE','UNCERTAIN'].includes(item.before_visibility)||['NOT_VISIBLE','UNCERTAIN'].includes(item.after_visibility))errors.push(vid+'：確定事件需可見證據；否則保留不確定');}}
      }
      if(v.review_status==='EXHAUSTIVELY_REVIEWED'&&(!coversFull(v.reviewed_intervals,v.source_duration_s)||!attestations.slice(0,4).every(k=>v.coverage_attestations[k])))errors.push(vid+'：全片審閱需完整區間與四項人工確認');
      if(v.event_list_exhaustiveness!==exhaustiveness(v))errors.push(vid+'：事件完整性與確認／不確定區間不一致');
    }
    if(seenVideos.size!==expected.size||[...expected.keys()].some(k=>!seenVideos.has(k)))errors.push('必須保留九支影片的紀錄');return errors;
  }
  function createSession(manifest,reviewer,assignment='',assignedIDs=manifest.videos.map(v=>v.video_id)) {
    const t=now();return {schema_version:'1.0',dataset_id:manifest.dataset_id,dataset_version:manifest.dataset_version,dataset_manifest_sha256:manifest.dataset_manifest_sha256,reviewer_id:reviewer.trim(),session_id:id('session'),assignment,created_at:t,updated_at:t,exported_at:t,export_kind:'BACKUP',videos:manifest.videos.map(meta=>({video_id:meta.video_id,source_sha256:meta.source_sha256,source_duration_s:meta.source_duration_s,assigned:assignedIDs.includes(meta.video_id),review_status:'NOT_STARTED',reviewed_intervals:[],events:[],states:[],uncertain_intervals:[],coverage_attestations:Object.fromEntries(attestations.map(k=>[k,false])),event_list_exhaustiveness:'UNKNOWN',notes:''}))};
  }
  function prepareExport(bundle,kind,manifest,schema) {
    const result=clone(bundle);result.exported_at=now();result.export_kind=kind;
    const errors=validate(result,manifest,schema);if(errors.length)throw Error(errors.slice(0,20).join('\n'));return result;
  }
  return {id,now,clone,strictParse,structural,validate,createSession,prepareExport,coversFull,exhaustiveness,nearest,attestations};
});
