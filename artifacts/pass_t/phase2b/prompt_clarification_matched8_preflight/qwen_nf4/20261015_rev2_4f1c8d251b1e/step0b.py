import core
import fixture_generator as gen

def run():
    core.authorities()
    assert core.read(core.OUT/'STEP_RECEIPT_0.json')['status']=='COMPLETE'
    assert not (core.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt').exists()
    manifest=[];files={}
    for scene,count,seed in gen.SCENARIOS:
        opaque='X_'+core.byte_sha(f'HOLDOUT_FIXTURE_REV2/{seed}'.encode())[:16]
        frames=[]
        for i in range(8):
            p=core.OUT/'model_visible'/'fixtures'/opaque/f'F{i+1:04d}.png';p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():raise FileExistsError(p)
            image=gen.render(seed,scene,i);image.save(p,format='PNG',optimize=False)
            pixel=core.byte_sha(image.tobytes());files[str(p.relative_to(core.OUT))]=core.sha(p)
            frames.append({'opaque_alias':f'F{i+1:04d}','source_frame_index':i,'synthetic_timestamp_s':i*0.5,
                'path':str(p.relative_to(core.OUT)),'file_sha256':core.sha(p),'canonical_rgb_pixel_sha256':pixel,'width':1280,'height':720})
        manifest.append({'fixture_id':opaque,'intended_stratum':f'SYNTHETIC_{count}_EVENT' if count!='WARMUP' else 'WARMUP',
          'script':scene,'seed':seed,'frames':frames,'dimensions':[1280,720],
          'target_convention':'one synthetic item; no reference media; no scene text answers',
          'rendering_rules':'fixture_generator.py render; contact/lift/lower trajectories are scripted; no real pixels',
          'intended_transitions_not_model_verified':True})
    h=core.save('SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json',{'private_answer_key':True,'scenarios':manifest,'generator_sha256':core.sha(core.OUT/'fixture_generator.py'),
      'evaluation_scenarios':6,'warmup_scenarios':1,'synthetic_only':True,'phase2a_pixel_reads':0,'reuse_capacity_images':False,
      'limitations':['2.5D procedural desk/hand-like rendering is not real-world video','Scripted transitions are designer intention, not VLM-recognized event GT','Same author knows scenario concepts; cryptographic locking is not conceptual blinding']})
    lock={'kind':'ENGINEERING_SYNTHETIC_HOLDOUT_LOCK_NOT_PROTOCOL_FREEZE','fixture_manifest_sha256':h,
      'generator_sha256':core.sha(core.OUT/'fixture_generator.py'),'model_visible_frames_sha256':files,
      'step0_receipt_sha256':core.sha(core.OUT/'STEP_RECEIPT_0.json'),'prompt_file_absent_at_lock':True,
      'no_model_calls':True,'model_visible_names_opaque':True}
    lock_id=core.byte_sha(core.canon(lock));core.save(f'fixture_private/locks/{lock_id}/lock.json',lock)
    core.save('SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json',{**lock,'content_id':lock_id})
    for n in files:(core.OUT/n).chmod(0o444)
    (core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json').chmod(0o444)
    (core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json').chmod(0o444)
    core.receipt('0B',[core.OUT/'STEP_RECEIPT_0.json',core.OUT/'fixture_generator.py'],
      [core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json',core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json'],lock_content_id=lock_id)
    print({'holdout':6,'warmup':1,'frames':56,'lock_content_id':lock_id,'manifest_sha256':h,'prompt_absent_at_lock':True})
if __name__=='__main__':run()
