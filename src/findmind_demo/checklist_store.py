"""Local preferences and user attestations, deliberately separate from Graph IO."""
from contextlib import contextmanager
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import time
import uuid


def now():return datetime.now(timezone.utc).isoformat()


class ChecklistStore:
    def __init__(self,root):
        self.directory=Path(root)/'artifacts/findmind_demo'
        self.path=self.directory/'checklist_state.json'

    @contextmanager
    def _lock(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        with (self.directory/'checklist_state.lock').open('a+b') as lock:
            lock.seek(0,2)
            if lock.tell()==0:lock.write(b'0');lock.flush()
            deadline=time.monotonic()+3
            while True:
                try:
                    lock.seek(0)
                    if os.name=='nt':
                        import msvcrt
                        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                    else:
                        import fcntl
                        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic()>deadline:raise RuntimeError('清單正在由另一個視窗儲存，請稍後再試。')
                    time.sleep(.03)
            try:yield
            finally:
                lock.seek(0)
                if os.name=='nt':msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(lock,fcntl.LOCK_UN)

    def _read(self):
        if self.path.exists():
            value=json.loads(self.path.read_text(encoding='utf8'))
            if value.get('version')!=1:raise ValueError('Unsupported checklist storage version')
            return value
        return dict(version=1,items=[dict(item_id=uuid.uuid4().hex,label=label,category=category,enabled=True)
            for label,category in [('手機','phone'),('鑰匙','keys'),('錢包','wallet')]],checks=[],active_by_memory={})

    def _write(self,value):
        temp=self.path.with_name(self.path.name+'.'+uuid.uuid4().hex+'.tmp')
        with temp.open('x',encoding='utf8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.replace(temp,self.path)

    def read(self):
        with self._lock():
            value=self._read()
            if not self.path.exists():self._write(value)
            return value

    @staticmethod
    def item_values(label,category):
        label=label.strip();category=category.strip().lower()
        if not 1<=len(label)<=60 or not 1<=len(category)<=80 or any(ord(c)<32 for c in label+category):
            raise ValueError('請提供簡短物品名稱與搜尋類別。')
        return label,category

    def add(self,label,category,enabled=True):
        label,category=self.item_values(label,category)
        with self._lock():
            value=self._read();item=dict(item_id=uuid.uuid4().hex,label=label,category=category,enabled=bool(enabled))
            if len(value['items'])>=30:raise ValueError('本機 Demo 清單最多 30 個物品。')
            value['items'].append(item);self._write(value);return item

    def update(self,item_id,*,label,category,enabled):
        label,category=self.item_values(label,category)
        with self._lock():
            value=self._read();item=next((i for i in value['items'] if i['item_id']==item_id),None)
            if not item:raise ValueError('Item no longer exists')
            item.update(label=label,category=category,enabled=bool(enabled));self._write(value)

    def remove(self,item_id):
        with self._lock():
            value=self._read();value['items']=[i for i in value['items'] if i['item_id']!=item_id];self._write(value)

    def start(self,memory_id,*,new=False,request_id=None,purpose='USER_DEPARTURE'):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',memory_id):raise ValueError('Invalid memory session')
        if purpose not in {'USER_DEPARTURE','DEMO_PRESENTATION'}:raise ValueError('Invalid departure-check purpose')
        with self._lock():
            value=self._read()
            if request_id:
                duplicate=next((c for c in value['checks'] if c.get('request_id')==request_id),None)
                if duplicate:
                    if duplicate['memory_session_id']!=memory_id:raise ValueError('Request already belongs to another memory')
                    return duplicate
            active=value['active_by_memory'].get(memory_id)
            if active and not new:return next(c for c in value['checks'] if c['check_id']==active)
            check=dict(check_id=uuid.uuid4().hex,memory_session_id=memory_id,created=now(),updated=now(),
                request_id=request_id,purpose=purpose,items=[dict(i) for i in value['items'] if i['enabled']],confirmations={},events=[],
                status='OPEN',confirmation_source='EXPLICIT_USER_ACTION_ONLY')
            if not check['items']:check['status']='NO_ENABLED_ITEMS'
            value['checks'].append(check);value['active_by_memory'][memory_id]=check['check_id'];self._write(value)
            return check

    def set_packed(self,check_id,item_id,packed):
        if not isinstance(packed,bool):raise ValueError('Explicit boolean user confirmation required')
        with self._lock():
            value=self._read();check=next((c for c in value['checks'] if c['check_id']==check_id),None)
            if not check or value['active_by_memory'].get(check['memory_session_id'])!=check_id:raise ValueError('此檢查已不是目前檢查，請重新整理。')
            if item_id not in {i['item_id'] for i in check['items']}:raise ValueError('Item is not part of this check')
            old=bool(check['confirmations'].get(item_id,{}).get('packed'))
            if old==packed:return check
            event=dict(event_id=uuid.uuid4().hex,item_id=item_id,packed=packed,time=now(),
                source='UI_DEMO_CONFIRMATION' if check.get('purpose')=='DEMO_PRESENTATION' else 'USER_MANUAL_CONFIRMATION')
            check['events'].append(event);check['confirmations'][item_id]=dict(event)
            check['updated']=event['time']
            check['status']='COMPLETE' if check['items'] and all(check['confirmations'].get(i['item_id'],{}).get('packed') for i in check['items']) else 'OPEN'
            self._write(value);return check

    def active(self,memory_id):
        value=self.read();cid=value['active_by_memory'].get(memory_id)
        return next((c for c in value['checks'] if c['check_id']==cid),None)
