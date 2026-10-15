"""Static-model-code positional calculation with CPU scalar tensors, no model."""
import core
import ast

def positions(torch,seconds,units,tokens_per_second):
    # Installed get_rope_index: expanded_range * second_per_grid_t * tokens_per_second,
    # then .long(). Common text-position offset is irrelevant to relative timing.
    values=torch.arange(units).view(-1,1)*torch.tensor(seconds,dtype=torch.float32)*tokens_per_second
    return values.long().flatten().tolist()

def main():
    core.authorities();torch=core.processor_guards()
    config_path=core.ROOT/'.models/Qwen2.5-VL-7B-Instruct/config.json'
    model_source=core.ROOT/'.venv/Lib/site-packages/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py'
    source=model_source.read_text();assert 'time_tensor_long = time_tensor.long()' in source
    factor=core.read(config_path)['vision_config']['tokens_per_second'];assert factor==2
    tests=[positions(torch,1.0,4,2)==[0,2,4,6],positions(torch,.99,4,2)==[0,1,3,5],len(positions(torch,1.,4,2))==4]
    assert all(tests)
    rows=[]
    for x in core.read(core.OUT/'matched8_results.json'):
        v=x['budgets']['VIDEO'];ticks=positions(torch,v['second_per_grid_ts'][0],v['temporal_patches'],factor)
        times=[ticks[i//v['temporal_patch_size']]/factor for i in range(8)]
        native=x['time']['native_window_relative_s'];deviation=[t-n for t,n in zip(times,native)]
        rows.append({'id':x['id'],'kind':x['kind'],'source':x.get('source'),
           'tokens_per_second':factor,'relative_temporal_position_ids_by_patch':ticks,
           'position_id_time_proxy_s_by_source_frame':times,'native_window_relative_s':native,
           'per_frame_proxy_deviation_s':deviation,'max_abs_proxy_deviation_s':max(abs(d) for d in deviation),
           'outcome':'FRAME_MATCHED_ONLY','claim_level':'STATIC_MODEL_POSITION_PROXY_NO_FORWARD',
           'runtime_consumption':'RUNTIME_CONSUMPTION_NOT_VERIFIED'})
    assert not torch.cuda.is_initialized()
    core.save('MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.json',{'source_sha256':core.sha(model_source),
       'config_sha256':core.sha(config_path),'rows':rows,'additional_cpu_tests_passed':3,'cuda_initialized':False})
    text='''# Model temporal-position 補充稽核（無forward）

Step2 report中的model_visible_temporal_patch_time是processor輸出的second_per_grid_ts重建，尚未套model位置ID整數化。本補充是解讀該數值的必要補充，不覆寫Step2回條／報告。

安裝中的get_rope_index在modeling_qwen2_5_vl.py:1097–1100用expanded_range × second_per_grid_t × tokens_per_second，再.long()。本地config實際tokens_per_second=2，並非source docstring例子25。使用CPUscalar Tensor重現相同dtype/運算，不建model、不呼叫model函式。offset扣除後可得relativeposition的秒數proxy，不證明實際runtime消費或模型理解物理時間。

| Case | Temporal position IDs | Per-frame time proxy | Max absolute deviation |
|---|---|---|---|
'''
    for r in rows:text+=f"| {r.get('source') or r['id']} | {r['relative_temporal_position_ids_by_patch']} | {r['position_id_time_proxy_s_by_source_frame']} | {r['max_abs_proxy_deviation_s']} |\n"
    text+='\n全部仍FRAME_MATCHED_ONLY。nativePTS只在private mapping；images/storyboard ORDER_ONLY且無時間秒數輸入。4時間位置不能證明8個alias逐張可辨。0.1s是未批准提案，不能拿較小nominalCFR誤差代替此proxy。追加3個CPU測試：exactgrid、float32/long truncation、4unit數量，全部通過。\n'
    core.save('MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.md',text)
    core.receipt('2_TIME_POSITION',[core.OUT/'STEP_RECEIPT_2.json',model_source,config_path],
       [core.OUT/'MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.json',core.OUT/'MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.md'],additional_cpu_tests_passed=3)
    print({'tokens_per_second':factor,'additional_cpu_tests':3,'cases':len(rows),'new_model_calls':0})
if __name__=='__main__':main()
