"""Native Tk human viewer. No network, whole source video, or automated answers."""
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk
from .phase1c_common import OUT, read, write, sha, now
from .phase1c_policy import verify_freeze
from .phase1c_responses import validate_response, load_reviews


class HumanSeedViewer:
    def __init__(self,root):
        self.root=root;self.base=OUT/'human_seed_review';self.receipt=verify_freeze()
        self.manifest=read(self.base/'review_manifest.json');self.items=self.manifest['items'];self.playing=False
        self.root.title('FindMind — Seven-window human seed review (local only)');self.root.geometry('1380x940')
        self.pack=tk.StringVar();self.reviewer=tk.StringVar();self.decision=tk.StringVar();self.candidate=tk.StringVar()
        self.support=tk.StringVar();self.uncertainty=tk.StringVar();self.confidence=tk.StringVar();self.human=tk.BooleanVar(value=False)
        self.exposed=tk.StringVar();self.dependent=tk.StringVar();self.claims=tk.StringVar();self.contradiction=tk.StringVar()
        self.citations=[];self.reference_vars={};self.frame_index=0
        top=ttk.Frame(root);top.pack(fill='x');ttk.Label(top,text='Case').pack(side='left')
        self.pack_box=ttk.Combobox(top,textvariable=self.pack,values=[e['pack_id'] for e in self.items],state='readonly',width=20)
        self.pack_box.pack(side='left');self.pack_box.bind('<<ComboboxSelected>>',lambda e:self.load_item())
        self.progress=ttk.Label(top);self.progress.pack(side='left',padx=12)
        self.header=ttk.Label(root,wraplength=1320);self.header.pack(fill='x',padx=8,pady=5)
        body=ttk.Frame(root);body.pack(fill='both',expand=True)
        left=ttk.Frame(body);left.pack(side='left',fill='both',expand=True)
        self.canvas=tk.Canvas(left,width=860,height=490,bg='black');self.canvas.pack()
        self.frame_label=ttk.Label(left);self.frame_label.pack()
        controls=ttk.Frame(left);controls.pack()
        ttk.Button(controls,text='Previous frame',command=lambda:self.step(-1)).pack(side='left')
        ttk.Button(controls,text='Play / Pause full-rate',command=self.toggle_play).pack(side='left')
        ttk.Button(controls,text='Next frame',command=lambda:self.step(1)).pack(side='left')
        ttk.Button(controls,text='Cite displayed frame',command=self.cite).pack(side='left')
        self.slider=ttk.Scale(left,from_=0,to=1,command=self.slide);self.slider.pack(fill='x')
        self.observations_label=ttk.Label(left,wraplength=860);self.observations_label.pack(fill='x',padx=5)
        self.references_frame=ttk.LabelFrame(left,text='REFERENCE_PRE_WINDOW — reference crops, never window evidence')
        self.references_frame.pack(fill='x',padx=5,pady=8)
        self.provenance=ttk.Label(left,wraplength=850);self.provenance.pack(fill='x',padx=5)
        right=ttk.Frame(body);right.pack(side='right',fill='y',padx=12)
        ttk.Label(right,text='Which candidate is supported as the original-seed target?',wraplength=450).pack(anchor='w')
        def combo(label,var,values):
            ttk.Label(right,text=label,wraplength=450).pack(anchor='w',pady=(6,0))
            box=ttk.Combobox(right,textvariable=var,values=values,state='readonly',width=47);box.pack(anchor='w');return box
        ttk.Label(right,text='Type your actual reviewer ID').pack(anchor='w')
        ttk.Entry(right,textvariable=self.reviewer,width=49).pack(anchor='w')
        combo('Decision (no forced choice)',self.decision,['SELECT_LOCAL_CANDIDATE','UNRESOLVED','NO_VISIBLE_TARGET','MULTIPLE_PLAUSIBLE_TARGETS'])
        self.candidate_box=combo('Existing local candidate (ascending IDs)',self.candidate,[])
        combo('Provenance support',self.support,['RECORDED_PROVENANCE_EDGE','HUMAN_VISUAL_LOCALIZATION_ONLY','NONE'])
        combo('Uncertainty',self.uncertainty,['LOCAL_SELECTION_ONLY','UNCERTAIN','UNRESOLVED'])
        combo('Your certainty (frozen response field)',self.confidence,['LOW','MEDIUM','HIGH'])
        self.cited_label=ttk.Label(right,text='Evidence frames: none',wraplength=450);self.cited_label.pack(anchor='w',pady=5)
        ttk.Button(right,text='Clear evidence citations',command=self.clear_citations).pack(anchor='w')
        ttk.Label(right,text='Rationale (required; no event-answer reasoning)').pack(anchor='w')
        self.rationale=tk.Text(right,width=55,height=5,wrap='word');self.rationale.pack(anchor='w')
        combo('Have you viewed event reference labels for this pack?',self.exposed,['No','Yes'])
        combo('Does your selection depend on interpreting an event answer?',self.dependent,['No','Yes'])
        combo('Does this response claim a global physical identity?',self.claims,['No','Yes'])
        combo('Is contradictory candidate evidence still unresolved?',self.contradiction,['No','Yes'])
        ttk.Checkbutton(right,text='I am the human reviewer and attest to this submission',variable=self.human).pack(anchor='w',pady=7)
        self.save_button=ttk.Button(right,text='Save immutable human response',command=self.save);self.save_button.pack(anchor='w')
        ttk.Label(right,text='Unresolved is valid. If event interpretation is necessary, choose UNRESOLVED. Exposure/identity claims prevent seed eligibility. Close and reopen to resume; saved responses are read-only.',wraplength=450).pack(anchor='w',pady=7)
        self.pack.set(self.items[0]['pack_id']);self.load_item()

    def load_item(self):
        self.playing=False
        entry=next(e for e in self.items if e['pack_id']==self.pack.get());path=self.base/entry['item_path']
        if sha(path)!=entry['item_sha256']:raise ValueError('Review package changed')
        self.entry=entry;self.folder=path.parent;self.item=read(path);self.frame_index=0
        for var in [self.decision,self.candidate,self.support,self.uncertainty,self.confidence,self.exposed,self.dependent,self.claims,self.contradiction]:var.set('')
        self.human.set(False);self.rationale.delete('1.0','end');self.clear_citations()
        self.header.config(text=f"{self.item['pack_id']} · source identifier {self.item['source_video_identifier']} · authorized [{self.item['window_start_s']:.6f}, {self.item['window_end_s']:.6f}) s · original seed track {self.item['original_seed_track']} · seed observations: in-window {self.item['original_seed_observations_in_window']}, pre-window {self.item['original_seed_observations_pre_window']}\nLocal candidates and pre-window references do not establish global physical identity. Source causality remains unverified.")
        self.candidate_box.config(values=[c['candidate_id'] for c in self.item['candidates']])
        self.slider.config(to=max(0,len(self.item['frames'])-1));self.slider.set(0)
        for child in self.references_frame.winfo_children():child.destroy()
        self.reference_vars={};self.ref_photos=[]
        for ref in self.item['references']:
            frame=ttk.Frame(self.references_frame);frame.pack(side='left',padx=5)
            with self.verified_image(ref) as im:
                thumb=im.copy();thumb.thumbnail((215,120));photo=ImageTk.PhotoImage(thumb)
            self.ref_photos.append(photo);label=ttk.Label(frame,image=photo);label.pack()
            label.bind('<Double-1>',lambda e,r=ref:self.enlarge_reference(r))
            var=tk.BooleanVar(value=False);self.reference_vars[ref['reference_id']]=var
            ttk.Checkbutton(frame,text=f"Used {ref['reference_id']} · {ref['source_timestamp_s']:.3f}s",variable=var).pack()
        if not self.item['references']:ttk.Label(self.references_frame,text='No authorized seed reference. UNRESOLVED is permitted.').pack()
        self.provenance.config(text='Recorded source provenance (causal cutoff applied; upstream origin unverified):\n'+'\n'.join(self.item['source_provenance_references']))
        reviews=load_reviews();row=next(r for r in reviews['items'] if r['pack_id']==self.pack.get())
        self.progress.config(text=f"Completed: {reviews['completed']}/7 · current: {row['human_review_status']}")
        exists=(self.base/'responses'/f'{self.pack.get()}.json').exists()
        self.save_button.config(state='disabled' if exists or reviews['completed']==7 else 'normal')
        self.show_frame()

    def enlarge_reference(self,ref):
        window=tk.Toplevel(self.root);window.title('REFERENCE_PRE_WINDOW '+ref['reference_id'])
        with self.verified_image(ref) as image:photo=ImageTk.PhotoImage(image.copy())
        label=ttk.Label(window,image=photo);label.image=photo;label.pack()
        ttk.Label(window,text='Reference only, not in-window evidence.').pack()

    def show_frame(self):
        f=self.item['frames'][self.frame_index]
        with self.verified_image(f) as image:
            original=image.size;image.thumbnail((860,490));size=image.size;self.photo=ImageTk.PhotoImage(image)
        self.canvas.delete('all');self.canvas.create_image(0,0,anchor='nw',image=self.photo)
        sx,sy=size[0]/original[0],size[1]/original[1]
        obs=[o for o in self.item['observations'] if o['source_frame_index']==f['source_frame_index']]
        for o in obs:
            x1,y1,x2,y2=o['bbox'];self.canvas.create_rectangle(x1*sx,y1*sy,x2*sx,y2*sy,outline='#00b4b4',width=2)
            self.canvas.create_text(x1*sx,y1*sy,anchor='sw',fill='#00b4b4',text=o['candidate_id'] or o['observation_id'])
        self.frame_label.config(text=f"{f['frame_id']} · source frame {f['source_frame_index']} · native PTS {f['source_timestamp_s']:.6f}s")
        self.observations_label.config(text='Exact observed references: '+(', '.join(o['observation_id'] for o in obs) or 'none; no interpolated boxes'))

    def verified_image(self,asset):
        path=(self.folder/asset['image_path']).resolve()
        if not path.is_relative_to(self.folder.resolve()) or sha(path)!=asset['sha256']:
            raise ValueError('Review asset changed or escaped bounded package')
        return Image.open(path)

    def slide(self,value):
        if not hasattr(self,'item'):return
        self.frame_index=max(0,min(len(self.item['frames'])-1,int(float(value))));self.show_frame()

    def step(self,delta):
        self.playing=False;self.frame_index=max(0,min(len(self.item['frames'])-1,self.frame_index+delta))
        self.slider.set(self.frame_index);self.show_frame()

    def toggle_play(self):
        self.playing=not self.playing
        if self.playing:self.tick()

    def tick(self):
        if not self.playing:return
        if self.frame_index>=len(self.item['frames'])-1:self.playing=False;return
        delay=max(1,round(1000*(self.item['frames'][self.frame_index+1]['source_timestamp_s']-self.item['frames'][self.frame_index]['source_timestamp_s'])))
        self.frame_index+=1;self.slider.set(self.frame_index);self.show_frame();self.root.after(delay,self.tick)

    def cite(self):
        id_=self.item['frames'][self.frame_index]['frame_id']
        if id_ not in self.citations:self.citations.append(id_)
        self.citations.sort();self.cited_label.config(text='Evidence frames: '+', '.join(self.citations))

    def clear_citations(self):
        self.citations=[]
        if hasattr(self,'cited_label'):self.cited_label.config(text='Evidence frames: none')

    def save(self):
        # This callback is deliberately not called by preparation/tests/agent.
        if not self.human.get() or not self.reviewer.get().strip():
            messagebox.showerror('Missing human attestation','Type your reviewer ID and confirm human authorship.');return
        if any(v.get() not in ['No','Yes'] for v in [self.exposed,self.dependent,self.claims,self.contradiction]):
            messagebox.showerror('Missing attestations','Answer all four Yes/No questions.');return
        receipt=verify_freeze();decision=self.decision.get();selected=self.candidate.get() if decision=='SELECT_LOCAL_CANDIDATE' else None
        stamp=now();frames={f['frame_id']:f for f in self.item['frames']};rationale=self.rationale.get('1.0','end').strip()
        cited=[frames[x] for x in self.citations]
        obs=[o['observation_id'] for o in self.item['observations'] if o['candidate_id']==selected and
             f"S{o['source_frame_index']:06d}" in self.citations] if selected else []
        value={'schema_version':'HUMAN_SEED_REVIEW_WRAPPER_V1',
               'primary_response':{'pack_id':self.pack.get(),'selected_local_track_id':selected,
                   'answer_type':'SELECTED_CANDIDATE' if selected else decision,'annotator_id':self.reviewer.get().strip(),
                   'timestamp':stamp,'frames_reviewed':[f['source_frame_index'] for f in cited],'notes':rationale,
                   'confidence':self.confidence.get(),'provenance':'HUMAN_SEEDED','global_identity_authority':False},
               'details':{'review_decision':decision,'selected_local_candidate_id':selected,
                   'reviewed_frame_ids':self.citations.copy(),'supporting_observation_ids':obs,
                   'source_provenance_references':self.item['source_provenance_references'],
                   'provenance_support':self.support.get(),'rationale':rationale,'uncertainty_status':self.uncertainty.get(),
                   'reference_material_used':[id_ for id_,var in self.reference_vars.items() if var.get()],
                   'contradictory_candidate_evidence':self.contradiction.get()=='Yes'},
               'attestations':{'human_attestation':True,'event_labels_viewed_for_this_pack':self.exposed.get()=='Yes',
                   'selection_depends_on_event_interpretation':self.dependent.get()=='Yes','claims_global_identity':self.claims.get()=='Yes'},
               'submission':{'submitted_via':'human_seed_review_viewer','automatic_timestamp_utc':stamp,
                   'timestamp_recorded_automatically':True,'submission_id':str(uuid.uuid4()),
                   'policy_md_sha256':receipt['policy_md_sha256'],'policy_json_sha256':receipt['policy_json_sha256'],
                   'review_item_sha256':self.entry['item_sha256']}}
        primary=read(OUT/'contracts/PASS_T_HUMAN_SEED_RESPONSE_SCHEMA_V1.json')
        companion=read(OUT/'contracts/PASS_T_HUMAN_SEED_REVIEW_WRAPPER_SCHEMA_V1.json')
        result=validate_response(value,self.item,receipt,primary,companion,self.entry['item_sha256'])
        if not result['valid']:messagebox.showerror('Response needs correction','\n'.join(result['errors']));return
        path=self.base/'responses'/f'{self.pack.get()}.json'
        try:write(path,value,exclusive=True)
        except FileExistsError:messagebox.showerror('Already saved','Original immutable response preserved.');return
        messagebox.showinfo('Saved','Immutable human response saved. DEV eligible: '+str(result['dev_eligible']))
        self.load_item()


def run():
    root=tk.Tk();HumanSeedViewer(root);root.mainloop()
