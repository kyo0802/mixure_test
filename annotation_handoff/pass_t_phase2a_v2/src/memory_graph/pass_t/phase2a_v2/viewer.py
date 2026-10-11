"""Native bounded human reviewer. No network, heuristics or prior event answers."""
import copy
import time
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from .policy import ROOT, OUT, within, sha, utc, verify_gate, frozen_schema
from .projection import load_manifest, load_item, load_backend
from .storage import progress, round_linkage, submit, attach_backend
from .validation import validate

LABELS = {
    'reviewer_id': '審閱者 ID', 'window_outcome': '整個視窗的判定', 'events': '已確認事件（可多筆）',
    'unmodeled_observations': '兩種事件以外的觀察', 'coverage_assessment': '全視窗可判定性（不是三張圖就能證明）',
    'coverage_citations': '起／中／末 COVERAGE 引用', 'last_confirmed_state': '最後直接確認的物理狀態',
    'last_confirmed_state_description': 'OTHER_OBSERVED 的實際支持方式', 'last_confirmed_frame_id': '最後確認的影格',
    'last_confirmed_state_evidence': '支持最後狀態的 STATE 引用', 'last_confirmed_location_description': '直接可見的位置描述',
    'location_evidence_frame_ids': '位置支持影格', 'location_marker': '手動畫的位置（在左側畫面點／拖曳）',
    'visibility_at_window_end': '最後授權影格的能見度（獨立於物理狀態）',
    'unknown_or_unobserved_afterward': '最後確認後有未知／未觀察期間？',
    'subsequent_location': '後續位置（只允許窗內直接證據）', 'subsequent_location_description': '後續可見位置描述',
    'subsequent_location_evidence': '後續位置的 STATE 引用', 'subsequent_location_evidence_frame_ids': '後續位置影格',
    'target_identification_event_dependence': '認出目標是否依賴觀看事件？',
    'target_identification_event_dependence_rationale': '目標辨識依賴性的理由',
    'target_recognition_used_pre_window_reference': '認出目標時有使用窗前參考圖？',
    'uncertainty': '不確定性', 'status': '狀態', 'description': '具體描述', 'confidence': '主觀信心（非機率）',
    'human_rationale': '人工判斷理由', 'event_type': '事件類型', 'event_time': '事件時間／保守區間',
    'start_frame_id': '區間起點影格', 'end_frame_id': '區間終點影格',
    'evidence': '視覺證據引用', 'observed_actor_reference': '可見施作人（不推定身分）',
    'before_state': '前狀態（只記直接可見）', 'after_state': '後狀態（只記直接可見）',
    'chronology_uncertainty': '事件區間重疊／先後不確定？', 'state': '物理狀態', 'frame_id': '證據影格',
    'visibility': '能見度', 'observed_reason': '不可見的觀察理由', 'rationale': '可見證據理由',
    'evidence_frame_ids': '引用影格', 'human_attestation': '確認這是我親自審閱並提交的判斷',
    'unauthorized_future_material_viewed': '曾看未授權的未來影格',
    'unapproved_source_video_scrubbing': '曾任意瀏覽整支來源影片',
    'experimental_answer_keys_viewed': '曾看實驗答案／GT', 'model_predictions_viewed': '曾看模型事件預測',
    'previous_event_answers_viewed': '曾看先前事件答案', 'claims_global_identity': '主張全域物件身分',
    'claims_unsupported_track_extension': '主張未有支持的 track 延伸',
}
EXHAUSTIVE_LABELS = [
    '我已看完整個授權視窗。', '我已標出所有可確認的目標 PICKUP／PLACEMENT。',
    '沒有能隱藏額外事件的可見性、身分關聯或時間缺口。', '完整性只涵蓋 PICKUP／PLACEMENT，不涵蓋所有動作。']
AUTOMATIC_ROOT = {'schema_version', 'annotation_item_id', 'review_round', 'relabel_of', 'target_reference',
                  'same_reviewer_as_phase1c', 'interaction_metadata', 'provenance', 'last_confirmed_timestamp',
                  'observation_coverage_frame_ids', 'event_list_exhaustiveness', 'event_list_exhaustiveness_attestation',
                  'attestations'}


def omit_stale_completeness(value):
    value = copy.deepcopy(value)
    if value.get('window_outcome') != 'CONFIRMED_EVENTS':
        value.pop('event_list_exhaustiveness', None)
        value.pop('event_list_exhaustiveness_attestation', None)
    elif value.get('event_list_exhaustiveness') != 'EXHAUSTIVE_ATTESTED':
        value.pop('event_list_exhaustiveness_attestation', None)
    return value


def display_to_source(x, y, scale, offset, width=1280, height=720):
    scale_x, scale_y = scale if isinstance(scale, tuple) else (scale, scale)
    sx, sy = (x - offset[0]) / scale_x, (y - offset[1]) / scale_y
    if not 0 <= sx < width or not 0 <= sy < height:
        raise ValueError('點擊不在影像內')
    return sx, sy


def resolved(schema, definitions):
    if '$ref' in schema:
        schema = definitions[schema['$ref'].split('/')[-1]]
    if 'allOf' in schema and 'properties' not in schema:
        for part in schema['allOf']:
            if '$ref' in part or 'properties' in part:
                result = resolved(part, definitions)
                if result.get('type'):
                    return result
    return schema


class Form(ttk.Frame):
    """Structured schema controls; evidence/marker/time authority have dedicated controls."""
    def __init__(self, parent, schema, app, initial=None, context='root'):
        super().__init__(parent)
        self.app, self.context, self.getters, self.controls = app, context, {}, {}
        self.schema = resolved(schema, app.schema['$defs'])
        initial = initial or {}
        properties = self.schema.get('properties', {})
        for key, raw in properties.items():
            if context == 'root' and key in AUTOMATIC_ROOT:
                continue
            if key in ('source_timestamp_s', 'start_timestamp_s', 'end_timestamp_s'):
                continue
            if context == 'event' and key in ('annotation_item_id', 'event_id', 'local_candidate_reference', 'provenance'):
                continue
            if context == 'unmodeled' and key == 'observation_id':
                continue
            spec = resolved(raw, app.schema['$defs'])
            row = ttk.LabelFrame(self, text=LABELS.get(key, key))
            row.pack(fill='x', padx=5, pady=3)
            if key == 'location_marker':
                label = ttk.Label(row, text='尚未手動畫位置；不會複製偵測框')
                label.pack(anchor='w'); self.controls[key] = label
                ttk.Button(row, text='清除位置標記', command=app.clear_marker).pack(anchor='w')
                self.getters[key] = lambda: copy.deepcopy(app.marker)
                continue
            nullable = 'anyOf' in spec
            if nullable:
                parts = spec['anyOf']
                nonnull = next((resolved(part, app.schema['$defs']) for part in parts if part.get('type') != 'null'), {})
                if nonnull.get('type') == 'object':
                    value = [copy.deepcopy(initial.get(key))]
                    display = ttk.Label(row, text='未提供（不推定狀態）'); display.pack(anchor='w')
                    def edit(value=value, display=display, spec=nonnull, key=key):
                        result = app.object_dialog(spec, value[0], context='state')
                        if result is not None:
                            value[0] = result; display.config(text='已輸入；可重新編輯')
                    ttk.Button(row, text='輸入／編輯', command=edit).pack(side='left')
                    ttk.Button(row, text='不提供', command=lambda v=value, d=display: (v.__setitem__(0, None), d.config(text='未提供'))).pack(side='left')
                    self.getters[key] = lambda v=value: copy.deepcopy(v[0])
                    continue
                spec = nonnull
            enum = spec.get('enum')
            if key.endswith('frame_id'):
                enum = [f['frame_id'] for f in app.item['visual']['frames']]
            if key == 'frame_id' and context == 'visibility':
                value = app.item['visual']['frames'][-1]['frame_id']
                ttk.Label(row, text=value + '（固定最後授權影格）').pack(anchor='w')
                self.getters[key] = lambda v=value: v
            elif enum is not None:
                var = tk.StringVar(master=app.root, value='' if initial.get(key) is None else str(initial[key]))
                combo = ttk.Combobox(row, textvariable=var, values=[''] + [str(v) for v in enum if v is not None], state='readonly', width=46)
                combo.pack(fill='x'); self.controls[key] = var
                self.getters[key] = lambda v=var, n=nullable or None in enum: v.get() or (None if n else '')
                if key.endswith('frame_id'):
                    ttk.Button(row, text='使用目前顯示影格', command=lambda v=var: v.set(app.current()['frame_id'])).pack(anchor='w')
            elif spec.get('type') == 'boolean':
                var = tk.StringVar(master=app.root, value='' if key not in initial else ('是' if initial[key] else '否'))
                ttk.Combobox(row, textvariable=var, values=['', '是', '否'], state='readonly').pack(fill='x')
                self.controls[key] = var
                self.getters[key] = lambda v=var: True if v.get() == '是' else False if v.get() == '否' else ''
            elif spec.get('type') == 'object':
                context_ = 'visibility' if key == 'visibility_at_window_end' else key
                nested = Form(row, spec, app, initial.get(key), context=context_)
                nested.pack(fill='x'); self.getters[key] = nested.value
                self.controls[key] = nested
            elif spec.get('type') == 'array':
                values = copy.deepcopy(initial.get(key, []))
                listing = tk.Listbox(row, height=3, exportselection=False)
                listing.pack(fill='x')
                def refresh(values=values, listing=listing):
                    listing.delete(0, 'end')
                    for index, value in enumerate(values):
                        if isinstance(value, dict):
                            label = value.get('event_type') or value.get('role') or value.get('description') or str(value)
                            label += ' ' + value.get('frame_id', '')
                        else:
                            label = str(value)
                        listing.insert('end', f'{index + 1}. {label}')
                refresh()
                item_spec = resolved(spec.get('items', {}), app.schema['$defs'])
                citation_array = 'source_observation_ids' in item_spec.get('properties', {})
                def add(values=values, refresh=refresh, item_spec=item_spec, key=key, citation_array=citation_array):
                    if citation_array:
                        chosen = app.choose_citations()
                        values.extend(copy.deepcopy(chosen))
                    elif item_spec.get('type') == 'object':
                        context_ = 'event' if key == 'events' else 'unmodeled'
                        result = app.object_dialog(item_spec, context=context_)
                        if result is not None:
                            if key == 'events':
                                free_id = next(i for i in range(1, 1000) if f'EVT{i:03d}' not in {e['event_id'] for e in values})
                                result.update(annotation_item_id=app.item['annotation_item_id'],
                                              event_id=f'EVT{free_id:03d}', local_candidate_reference=app.item['selected_local_candidate_id'],
                                              provenance={'annotation_origin': 'HUMAN', 'evidence_scope': 'AUTHORIZED_WINDOW_ONLY'})
                            elif key == 'unmodeled_observations':
                                free_id = next(i for i in range(1, 1000) if f'UM{i:03d}' not in {e['observation_id'] for e in values})
                                result['observation_id'] = f'UM{free_id:03d}'
                            values.append(result)
                    else:
                        values.extend(app.choose_frames())
                    refresh()
                def remove(values=values, listing=listing, refresh=refresh):
                    for index in reversed(listing.curselection()):
                        del values[index]
                    refresh()
                def edit(values=values, listing=listing, refresh=refresh, spec=item_spec, key=key, citation_array=citation_array):
                    selection = listing.curselection()
                    if selection and isinstance(values[selection[0]], dict) and not citation_array:
                        index = selection[0]
                        old = values[index]
                        result = app.object_dialog(spec, old, 'event' if key == 'events' else 'unmodeled')
                        if result is not None:
                            for field in ('annotation_item_id', 'event_id', 'local_candidate_reference', 'provenance', 'observation_id'):
                                if field in old:
                                    result[field] = old[field]
                            values[index] = result; refresh()
                buttons = ttk.Frame(row); buttons.pack(fill='x')
                ttk.Button(buttons, text='加入', command=add).pack(side='left')
                ttk.Button(buttons, text='移除', command=remove).pack(side='left')
                if not citation_array and item_spec.get('type') == 'object':
                    ttk.Button(buttons, text='編輯', command=edit).pack(side='left')
                def move(delta, values=values, listing=listing, refresh=refresh):
                    chosen = listing.curselection()
                    if chosen and 0 <= chosen[0] + delta < len(values):
                        i, j = chosen[0], chosen[0] + delta
                        values[i], values[j] = values[j], values[i]; refresh(); listing.selection_set(j)
                ttk.Button(buttons, text='↑', command=lambda m=move: m(-1)).pack(side='left')
                ttk.Button(buttons, text='↓', command=lambda m=move: m(1)).pack(side='left')
                self.getters[key] = lambda v=values: copy.deepcopy(v)
            else:
                var = tk.StringVar(master=app.root, value=initial.get(key) or '')
                ttk.Entry(row, textvariable=var, width=48).pack(fill='x')
                self.controls[key] = var
                self.getters[key] = lambda v=var, n=nullable: v.get().strip() or (None if n else '')

    def value(self):
        result = {key: getter() for key, getter in self.getters.items()}
        table = {f['frame_id']: f['source_timestamp_s'] for f in self.app.item['visual']['frames']}
        for fid, time in (('frame_id', 'source_timestamp_s'), ('start_frame_id', 'start_timestamp_s'), ('end_frame_id', 'end_timestamp_s')):
            if fid in result:
                result[time] = table.get(result[fid])
        return result


class Viewer:
    def __init__(self, master, out=OUT, round_=1):
        self.root, self.out, self.round = master, out, round_
        self.receipt, self.schema = verify_gate(out), frozen_schema()
        self.manifest = load_manifest(out)
        self.entries = [e for e in self.manifest['items'] if round_ == 1 or e['annotation_item_id'] in self.manifest['repeat_subset']]
        self.index, self.position, self.playing, self.timer, self.marker, self.drag = 0, 0, False, None, None, None
        self.pool, self.logs, self.opened, self.dirty = [], [], [], False
        self.root.title('FindMind — Pass T Phase 2a V2 人工事件審閱')
        self.root.geometry(f'{min(1440, self.root.winfo_screenwidth()-80)}x{min(940, self.root.winfo_screenheight()-100)}')
        self.root.rowconfigure(1, weight=1); self.root.columnconfigure(0, weight=1)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        header = ttk.Frame(master); header.grid(row=0, column=0, sticky='ew')
        ttk.Button(header, text='上一個視窗', command=lambda: self.navigate(-1)).pack(side='left')
        ttk.Button(header, text='下一個視窗', command=lambda: self.navigate(1)).pack(side='left')
        self.progress_label = ttk.Label(header); self.progress_label.pack(side='left', padx=10)
        body = ttk.Panedwindow(master, orient='horizontal'); body.grid(row=1, column=0, sticky='nsew')
        left_host = ttk.Frame(body); right = ttk.Frame(body); body.add(left_host, weight=3); body.add(right, weight=2)
        self.evidence_scroll = tk.Canvas(left_host, width=820)
        evidence_bar = ttk.Scrollbar(left_host, orient='vertical', command=self.evidence_scroll.yview)
        evidence_bar.pack(side='right', fill='y'); self.evidence_scroll.pack(side='left', fill='both', expand=True)
        self.evidence_scroll.configure(yscrollcommand=evidence_bar.set)
        left = ttk.Frame(self.evidence_scroll)
        evidence_window = self.evidence_scroll.create_window((0, 0), window=left, anchor='nw')
        left.bind('<Configure>', lambda event: self.evidence_scroll.configure(scrollregion=self.evidence_scroll.bbox('all')))
        self.evidence_scroll.bind('<Configure>', lambda event: self.evidence_scroll.itemconfigure(evidence_window, width=event.width))
        self.identity = ttk.Label(left, wraplength=820); self.identity.pack(fill='x')
        self.canvas = tk.Canvas(left, width=820, height=350, bg='#202020'); self.canvas.pack(fill='x')
        self.canvas.bind('<ButtonPress-1>', self.mark_start); self.canvas.bind('<ButtonRelease-1>', self.mark_end)
        self.time_label = ttk.Label(left); self.time_label.pack(fill='x')
        controls = ttk.Frame(left); controls.pack(fill='x')
        ttk.Button(controls, text='◀ 上一格', command=lambda: self.frame_step(-1)).pack(side='left')
        ttk.Button(controls, text='播放／暫停', command=self.toggle_play).pack(side='left')
        ttk.Button(controls, text='下一格 ▶', command=lambda: self.frame_step(1)).pack(side='left')
        self.overlay = tk.StringVar(master=self.root, value='SELECTED_CANDIDATE_ONLY')
        overlay = ttk.Combobox(controls, textvariable=self.overlay, state='readonly',
                              values=['SELECTED_CANDIDATE_ONLY', 'OFF', 'ALL_CANDIDATES'], width=27)
        overlay.pack(side='left'); overlay.bind('<<ComboboxSelected>>', self.overlay_changed)
        self.slider = ttk.Scale(left, from_=0, to=1, command=self.slider_changed); self.slider.pack(fill='x')
        self.slider.bind('<ButtonPress-1>', lambda event: self.stop_play())
        ttk.Button(left, text='檢視目前影格的原始解析度（同一授權影格）', command=self.inspect_current).pack(anchor='w')
        ttk.Label(left, text='框只供視覺參考，不證明身分；禁止自動把 32=34 或 74=candidate_014。', wraplength=820).pack(fill='x')
        self.references = ttk.Frame(left); self.references.pack(fill='x')
        marks = ttk.Frame(left); marks.pack(fill='x')
        ttk.Label(marks, text='手動畫位置：').pack(side='left')
        self.mark_mode = tk.StringVar(master=self.root, value='OFF')
        ttk.Combobox(marks, textvariable=self.mark_mode, values=['OFF', 'POINT', 'BBOX'], state='readonly', width=10).pack(side='left')
        ttk.Label(marks, text='POINT 點一下；BBOX 拖曳。標記只屬於該影格。').pack(side='left')
        cite = ttk.LabelFrame(left, text='引用目前影格（先加入引用庫，再放入事件／狀態／coverage）'); cite.pack(fill='x')
        self.cite_kind, self.association = tk.StringVar(master=self.root), tk.StringVar(master=self.root)
        ttk.Combobox(cite, textvariable=self.cite_kind, values=self.schema['$defs']['citation']['properties']['kind']['enum'], state='readonly', width=34).pack(fill='x')
        ttk.Combobox(cite, textvariable=self.association, values=self.schema['$defs']['citation']['properties']['target_association']['enum'], state='readonly').pack(fill='x')
        ttk.Label(cite, text='直接證據：具體看見什麼目標、位於哪裡；偵測框不替代此判斷。').pack(anchor='w')
        self.cite_description = ttk.Entry(cite); self.cite_description.pack(fill='x')
        roles = ttk.Frame(cite); roles.pack(fill='x')
        for role in ('BEFORE', 'TRANSITION', 'AFTER', 'STATE', 'COVERAGE'):
            ttk.Button(roles, text=role, command=lambda r=role: self.add_citation(r)).pack(side='left')
        self.pool_list = tk.Listbox(cite, height=5, exportselection=False); self.pool_list.pack(fill='x')
        ttk.Button(cite, text='從引用庫移除（既有表單引用需另移除）', command=self.remove_citation).pack(anchor='w')
        self.scroll = tk.Canvas(right, width=520)
        scrollbar = ttk.Scrollbar(right, orient='vertical', command=self.scroll.yview)
        scrollbar.pack(side='right', fill='y'); self.scroll.pack(side='left', fill='both', expand=True)
        self.scroll.configure(yscrollcommand=scrollbar.set)
        self.form_holder = ttk.Frame(self.scroll)
        self.form_window = self.scroll.create_window((0, 0), window=self.form_holder, anchor='nw')
        self.form_holder.bind('<Configure>', lambda event: self.scroll.configure(scrollregion=self.scroll.bbox('all')))
        self.scroll.bind('<Configure>', lambda event: self.scroll.itemconfigure(self.form_window, width=event.width))
        footer = ttk.Frame(master); footer.grid(row=2, column=0, sticky='ew')
        ttk.Button(footer, text='檢查尚未提交的答案', command=self.preview).pack(side='left')
        self.save_button = ttk.Button(footer, text='確認並永久提交（不能覆寫）', command=self.save); self.save_button.pack(side='left')
        ttk.Button(footer, text='暫停／關閉', command=self.close).pack(side='left')
        self.feedback = tk.Text(master, height=4, wrap='word'); self.feedback.grid(row=3, column=0, sticky='ew')
        self.load()

    def current(self):
        return self.item['visual']['frames'][self.position]

    def load(self):
        self.stop_play()
        self.entry = self.entries[self.index]
        self.item = load_item(self.entry, self.out)
        self.backend = load_backend(self.entry, self.out)
        self.linkage = None
        if self.round == 2:
            try:
                self.linkage = round_linkage(self.item['annotation_item_id'], self.out)
            except ValueError as error:
                messagebox.showwarning('尚不能重複審閱', str(error))
        self.position, self.marker, self.pool, self.logs, self.opened = 0, None, [], [], []
        self.overlay.set('SELECTED_CANDIDATE_ONLY'); self.mark_mode.set('OFF')
        self.cite_kind.set(''); self.association.set(''); self.cite_description.delete(0, 'end'); self.pool_list.delete(0, 'end')
        for child in self.form_holder.winfo_children():
            child.destroy()
        self.form = Form(self.form_holder, self.schema, self)
        self.form.pack(fill='x')
        complete = ttk.LabelFrame(self.form_holder, text='CONFIRMED_EVENTS 的事件清單完整性'); complete.pack(fill='x', padx=5, pady=5)
        self.complete_frame = complete
        self.exhaustiveness = tk.StringVar(master=self.root)
        self.exhaust_combo = ttk.Combobox(complete, textvariable=self.exhaustiveness, state='readonly',
                                        values=['', 'EXHAUSTIVE_ATTESTED', 'NOT_ATTESTED', 'UNKNOWN'], width=42)
        self.exhaust_combo.pack(fill='x')
        ttk.Label(complete, text='有缺口可能隱藏事件 → 不能聲明 exhaustive。\n三張 coverage 引用不證明連續可判定性。', wraplength=490).pack(fill='x')
        self.exhaust_checks = []
        for label in EXHAUSTIVE_LABELS:
            var = tk.BooleanVar(master=self.root, value=False); self.exhaust_checks.append(var)
            ttk.Checkbutton(complete, text=label, variable=var).pack(anchor='w')
        self.exhaustiveness.trace_add('write', self.exhaustiveness_changed)
        self.form.controls['window_outcome'].trace_add('write', self.outcome_changed)
        self.outcome_changed()
        attest = ttk.LabelFrame(self.form_holder, text='人工聲明／資訊暴露（有發生請勾選，將保留但排除）'); attest.pack(fill='x', padx=5)
        self.attests = {}
        for key in self.schema['$defs']['attestations']['properties']:
            var = tk.BooleanVar(master=self.root, value=False); self.attests[key] = var
            ttk.Checkbutton(attest, text=LABELS[key], variable=var).pack(anchor='w')
        for child in self.references.winfo_children():
            child.destroy()
        for ref in self.item['visual']['references']:
            ttk.Button(self.references, text=ref['reference_id'] + ' 窗前參考（不可引用）', command=lambda r=ref: self.show_reference(r)).pack(side='left')
        self.slider.configure(to=len(self.item['visual']['frames']) - 1); self.slider.set(0)
        status = progress(self.out)
        completed = self.item['annotation_item_id'] in (status['completed_ids'] if self.round == 1 else status['completed_repeat_ids'])
        self.save_button.config(state='disabled' if completed or status['invalid_records'] or (self.round == 2 and not self.linkage) else 'normal')
        self.progress_label.config(text=f'第 {self.index+1}/{len(self.entries)} 窗｜第一輪 {status["valid_round1"]}/7｜無效紀錄 {status["invalid_records"]}｜第 {self.round} 輪；不顯示舊答案')
        self.identity.config(text=', '.join(self.item['original_pack_ids']) + f'｜{self.item["stratum"]}｜local target {self.item["selected_local_candidate_id"]}\nHUMAN_SEEDED 僅是人工局部定位，不證明全域身分；CAUSALITY_UNVERIFIED。')
        self.feedback.delete('1.0', 'end')
        if completed:
            self.feedback.insert('end', '此輪已提交；原答案保持不可覆寫且不顯示。')
        self.draw()

    def outcome_changed(self, *_):
        confirmed = self.form.controls['window_outcome'].get() == 'CONFIRMED_EVENTS'
        if confirmed:
            self.complete_frame.pack(fill='x', padx=5, pady=5)
        else:
            self.complete_frame.pack_forget()
            self.exhaustiveness.set('')
            for var in self.exhaust_checks:
                var.set(False)

    def exhaustiveness_changed(self, *_):
        if self.exhaustiveness.get() != 'EXHAUSTIVE_ATTESTED':
            for var in self.exhaust_checks:
                var.set(False)

    def draw(self):
        frame = self.current(); path = within(ROOT, frame['image_path'])
        if sha(path) != frame['sha256']:
            raise ValueError('影格 hash 改變，停止顯示')
        with Image.open(path) as image:
            width, height = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
            if width < 10: width = 820
            if height < 10: height = 350
            self.scale = min(width / image.width, height / image.height)
            size = (round(image.width * self.scale), round(image.height * self.scale))
            self.render_scale = (size[0] / image.width, size[1] / image.height)
            self.offset = ((width - size[0]) / 2, (height - size[1]) / 2)
            self.photo = ImageTk.PhotoImage(image.resize(size), master=self.root)
        self.canvas.delete('all'); self.canvas.create_image(*self.offset, image=self.photo, anchor='nw')
        if self.overlay.get() != 'OFF':
            for observation in self.item['observations']:
                if observation['source_frame_index'] != frame['source_frame_index']:
                    continue
                selected = observation['candidate_id'] == self.item['selected_local_candidate_id']
                if not selected and self.overlay.get() != 'ALL_CANDIDATES':
                    continue
                coords = [v * self.render_scale[i % 2] + self.offset[i % 2] for i, v in enumerate(observation['bbox'])]
                self.canvas.create_rectangle(*coords, outline='#00ff88' if selected else '#ffbb44', width=2)
                self.canvas.create_text(coords[0], coords[1], text=observation['candidate_id'], fill='white', anchor='sw')
        if self.marker and self.marker['frame_id'] == frame['frame_id']:
            coords = [v * self.render_scale[i % 2] + self.offset[i % 2] for i, v in enumerate(self.marker['coordinates'])]
            if self.marker['kind'] == 'POINT':
                x, y = coords; self.canvas.create_oval(x-5, y-5, x+5, y+5, outline='#ff44ee', width=3)
            else:
                self.canvas.create_rectangle(*coords, outline='#ff44ee', width=3)
        self.time_label.config(text=f'{frame["frame_id"]}｜native PTS {frame["source_timestamp_s"]:.9f} 秒｜{self.position+1}/{len(self.item["visual"]["frames"])}')

    def slider_changed(self, value):
        if hasattr(self, 'item'):
            self.position = max(0, min(len(self.item['visual']['frames']) - 1, round(float(value)))); self.draw()

    def frame_step(self, delta):
        self.stop_play(); self.slider.set(max(0, min(len(self.item['visual']['frames']) - 1, self.position + delta)))

    def stop_play(self):
        self.playing = False
        if self.timer:
            self.root.after_cancel(self.timer); self.timer = None

    def toggle_play(self):
        if self.playing:
            self.stop_play(); return
        self.play_anchor = (time.perf_counter(), self.current()['source_timestamp_s'])
        self.playing = True; self.tick()

    def tick(self):
        frames = self.item['visual']['frames']
        if not self.playing or self.position == len(frames) - 1:
            self.stop_play(); return
        target_elapsed = frames[self.position + 1]['source_timestamp_s'] - self.play_anchor[1]
        delay = max(1, round((target_elapsed - (time.perf_counter() - self.play_anchor[0])) * 1000))
        self.timer = self.root.after(delay, self.advance_play)

    def advance_play(self):
        self.timer = None; self.slider.set(self.position + 1); self.tick()

    def overlay_changed(self, *_):
        self.logs.append({'timestamp_utc': utc(), 'mode': self.overlay.get()}); self.draw()

    def show_reference(self, reference):
        path = within(ROOT, reference['image_path'])
        if sha(path) != reference['sha256']:
            raise ValueError('Reference hash mismatch')
        if reference['reference_id'] not in self.opened:
            self.opened.append(reference['reference_id'])
        window = tk.Toplevel(self.root); window.title('REFERENCE_PRE_WINDOW — 不可作事件／狀態引用')
        ttk.Label(window, text='只用於目標辨識；不可引用。').pack()
        with Image.open(path) as image:
            photo = ImageTk.PhotoImage(image.copy(), master=self.root)
        label = ttk.Label(window, image=photo); label.image = photo; label.pack()

    def inspect_current(self):
        self.stop_play()
        frame = self.current(); path = within(ROOT, frame['image_path'])
        if sha(path) != frame['sha256']:
            raise ValueError('Authorized image hash mismatch')
        window = tk.Toplevel(self.root)
        window.title(f'{frame["frame_id"]} — native PTS {frame["source_timestamp_s"]:.9f} 秒；同一影格')
        window.geometry(f'{min(1320, window.winfo_screenwidth()-80)}x{min(810, window.winfo_screenheight()-100)}')
        window.rowconfigure(0, weight=1); window.columnconfigure(0, weight=1)
        canvas = tk.Canvas(window)
        vertical = ttk.Scrollbar(window, command=canvas.yview)
        horizontal = ttk.Scrollbar(window, orient='horizontal', command=canvas.xview)
        canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        canvas.grid(row=0, column=0, sticky='nsew'); vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        with Image.open(path) as image:
            canvas.photo = ImageTk.PhotoImage(image.copy(), master=window)
        canvas.create_image(0, 0, image=canvas.photo, anchor='nw'); canvas.configure(scrollregion=(0, 0, 1280, 720))
        ttk.Button(window, text='關閉後引用此影格', command=window.destroy).grid(row=2, column=0)
        window.transient(self.root); window.grab_set(); self.root.wait_window(window)

    def add_citation(self, role):
        frame = self.current()
        ids = [o['observation_id'] for o in self.item['observations']
               if o['source_frame_index'] == frame['source_frame_index'] and o['candidate_id'] == self.item['selected_local_candidate_id']]
        kind, association = self.cite_kind.get(), self.association.get()
        description = self.cite_description.get().strip()
        if not kind or not association:
            messagebox.showerror('引用未完成', '請明確選擇引用種類與目標關聯。'); return
        if kind == 'DIRECT_VISUAL_ONLY' and (ids or not description):
            messagebox.showerror('直接引用不符合合約', '此影格不得有既有選定目標 observation；並需描述可見什麼及位置。'); return
        if kind == 'CANDIDATE_OBSERVATION_BACKED' and not ids:
            messagebox.showerror('沒有對應 observation', '請用 DIRECT_VISUAL_ONLY 並提供人工可見證據，不能延伸 track。'); return
        citation = {'frame_id': frame['frame_id'], 'source_timestamp_s': frame['source_timestamp_s'],
                    'role': role, 'kind': kind, 'source_observation_ids': ids if kind == 'CANDIDATE_OBSERVATION_BACKED' else [],
                    'visual_description': description or None, 'target_association': association}
        if citation in self.pool:
            messagebox.showwarning('重複引用', '此引用已在引用庫中。'); return
        self.pool.append(citation); self.pool_list.insert('end', f'{len(self.pool)}. {role} {frame["frame_id"]} {association} {kind}')

    def remove_citation(self):
        for index in reversed(self.pool_list.curselection()):
            del self.pool[index]
        self.pool_list.delete(0, 'end')
        for c in self.pool:
            self.pool_list.insert('end', f'{c["role"]} {c["frame_id"]} {c["target_association"]}')

    def choose(self, values, labels, title):
        window = tk.Toplevel(self.root); window.title(title); window.transient(self.root)
        listing = tk.Listbox(window, selectmode='extended', width=75, height=min(20, max(3, len(values))), exportselection=False)
        listing.pack(fill='both', expand=True)
        for label in labels: listing.insert('end', label)
        result = []
        def accept():
            result.extend(copy.deepcopy(values[i]) for i in listing.curselection()); window.destroy()
        ttk.Button(window, text='加入選定項目', command=accept).pack()
        ttk.Button(window, text='取消', command=window.destroy).pack()
        window.grab_set(); self.root.wait_window(window); return result

    def choose_citations(self):
        return self.choose(self.pool, [f'{c["role"]} {c["frame_id"]} {c["kind"]} {c["target_association"]} {c["visual_description"] or ""}' for c in self.pool], '選擇引用（可多選）')

    def choose_frames(self):
        frames = self.item['visual']['frames']
        return self.choose([f['frame_id'] for f in frames], [f'{f["frame_id"]} {f["source_timestamp_s"]:.9f}' for f in frames], '選擇授權影格（可多選）')

    def object_dialog(self, schema, initial=None, context='object'):
        window = tk.Toplevel(self.root); window.title('編輯 ' + LABELS.get(context, context)); window.geometry('650x800'); window.transient(self.root)
        canvas = tk.Canvas(window); scrollbar = ttk.Scrollbar(window, command=canvas.yview)
        scrollbar.pack(side='right', fill='y'); canvas.pack(fill='both', expand=True); canvas.config(yscrollcommand=scrollbar.set)
        form = Form(canvas, schema, self, initial, context); canvas.create_window((0, 0), window=form, anchor='nw', width=610)
        form.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        result = []
        def accept():
            result.append(form.value()); window.destroy()
        ttk.Button(window, text='保留到未提交草稿', command=accept).pack()
        ttk.Button(window, text='取消此次編輯', command=window.destroy).pack()
        window.grab_set(); self.root.wait_window(window)
        return result[0] if result else None

    def mark_start(self, event):
        if self.mark_mode.get() == 'OFF': return
        self.stop_play()
        try:
            self.drag = display_to_source(event.x, event.y, self.render_scale, self.offset)
        except ValueError: self.drag = None

    def mark_end(self, event):
        if self.drag is None: return
        try:
            end = display_to_source(event.x, event.y, self.render_scale, self.offset)
            kind = self.mark_mode.get()
            coords = list(end) if kind == 'POINT' else [min(self.drag[0], end[0]), min(self.drag[1], end[1]), max(self.drag[0], end[0]), max(self.drag[1], end[1])]
            if kind == 'BBOX' and (coords[0] == coords[2] or coords[1] == coords[3]): return
            self.marker = {'frame_id': self.current()['frame_id'], 'kind': kind, 'coordinates': coords,
                           'coordinate_system_id': 'REVIEW_FRAME_PIXELS_V1', 'origin': 'GUI_DRAWN'}
            self.form.controls['location_marker'].config(text=f'{kind} {self.marker["frame_id"]} {coords}')
            self.draw()
        except ValueError: pass
        finally: self.drag = None

    def clear_marker(self):
        self.marker = None
        if hasattr(self, 'form') and 'location_marker' in self.form.controls:
            self.form.controls['location_marker'].config(text='尚未手動畫位置')
        if hasattr(self, 'item'): self.draw()

    def draft(self):
        value = self.form.value()
        table = {f['frame_id']: f['source_timestamp_s'] for f in self.item['visual']['frames']}
        value['last_confirmed_timestamp'] = table.get(value['last_confirmed_frame_id'])
        value['observation_coverage_frame_ids'] = list(dict.fromkeys(c['frame_id'] for c in value['coverage_citations']))
        value['attestations'] = {key: var.get() for key, var in self.attests.items()}
        value['interaction_metadata'] = {'initial_overlay_mode': 'SELECTED_CANDIDATE_ONLY',
                                         'references_opened': list(self.opened), 'overlay_toggles': list(self.logs), 'metadata_is_advisory': True}
        if value['window_outcome'] == 'CONFIRMED_EVENTS':
            value['event_list_exhaustiveness'] = self.exhaustiveness.get()
            if self.exhaustiveness.get() == 'EXHAUSTIVE_ATTESTED':
                keys = self.schema['$defs']['event_list_exhaustiveness_attestation']['required']
                value['event_list_exhaustiveness_attestation'] = {k: var.get() for k, var in zip(keys, self.exhaust_checks)}
        return omit_stale_completeness(value)

    def preview(self):
        draft = self.draft()
        value = attach_backend(draft, self.item, self.entry, self.backend, self.receipt, self.round, self.linkage)
        result = validate(value, self.item, self.entry['item_sha256'], self.receipt, self.backend, self.linkage, self.manifest['repeat_subset'])
        self.feedback.delete('1.0', 'end')
        self.feedback.insert('end', '\n'.join(result['errors'] + result['exclusions'] + result['warnings']) or '合約檢查通過；尚未提交。這不證明視覺判斷正確。')
        return result

    def save(self):
        if not self.preview()['valid']: return
        if not messagebox.askyesno('永久提交', '提交後不能修改／覆寫。確定這是你親自完整審閱的答案？'): return
        try:
            result = submit(self.draft(), self.entry, self.round, self.out)
            self.feedback.delete('1.0', 'end'); self.feedback.insert('end', '已永久提交：' + result['path'])
            self.save_button.config(state='disabled')
        except (ValueError, OSError) as error:
            messagebox.showerror('提交未完成', str(error))

    def navigate(self, delta):
        if not messagebox.askyesno('切換視窗', '未提交草稿不會自動儲存。已提交答案保持原樣且不顯示。確定切換？'): return
        self.index = max(0, min(len(self.entries)-1, self.index+delta)); self.load()

    def close(self):
        if messagebox.askyesno('暫停審閱', '已提交答案會保留。未提交草稿將捨棄；要關閉嗎？'):
            self.stop_play(); self.root.destroy()


def launch(out=OUT, round_=1):
    verify_gate(out)
    root = tk.Tk()
    Viewer(root, out, round_)
    root.mainloop()
