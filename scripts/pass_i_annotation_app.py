"""Run with scripts/start_pass_i_annotation.ps1. No inference or identity writes."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import streamlit as st
from PIL import Image
from memory_graph.pass_i.common import OUT, read, read_lines, resolve
from memory_graph.pass_i.annotations import AnnotationStore, TAGS, CAUSES, EXCLUSIONS
from memory_graph.pass_i.dev_pilot_audit import FLAGS, audit as pilot_audit, flags as pilot_flags, save_flag, render_report

st.set_page_config(page_title='FindMind Pass I Annotation', layout='wide')
out = Path(os.environ.get('FINDMIND_PASS_I_DATASET', OUT))
workflow = st.sidebar.radio('Workflow', ['Identity Annotation', 'Evidence QC'])
if workflow == 'Evidence QC':
    from pass_i_evidence_qc_ui import render as render_evidence_qc
    render_evidence_qc(out)
    st.stop()
store = AnnotationStore(out)
manifest = out / 'manifests/pair_manifest.jsonl'
if not manifest.is_file():
    st.error('Dataset not built. Run scripts/build_pass_i.py first.')
    st.stop()
pairs = read_lines(manifest)
st.title('FindMind Pass I · Human Annotation')
pilot_file = out / 'manifests/dev_pilot_manifest.json'
pilot_entries = {}
pilot_active = False
if pilot_file.exists():
    scopes = ['DEV Pilot 0', 'Full dataset']
    pilot1_file = out / 'manifests/dev_pilot_1_manifest.json'
    pilot1_ready = pilot1_file.exists() and all(
        (out / 'prelabels/dev_pilot_1' / f"{entry['item_id']}.json").exists()
        for entry in read(pilot1_file)['items'])
    if pilot1_ready:
        scopes.insert(1, 'DEV Pilot 1')
    scope = st.sidebar.radio('Dataset scope', scopes)
    if scope in {'DEV Pilot 0', 'DEV Pilot 1'}:
        pilot_active = True
        pilot_manifest = read(pilot_file if scope == 'DEV Pilot 0' else pilot1_file)
        pilot_entries = {p['item_id']: p for p in pilot_manifest['items']}
        if scope == 'DEV Pilot 0':
            pairs = [p for p in pairs if p['item_id'] in pilot_entries and p['split'] == 'dev']
            store = AnnotationStore(out / 'annotations/dev_pilot', prelabels_out=out / 'prelabels/dev_pilot')
        else:
            pairs = pilot_manifest['items']
            store = AnnotationStore(out / 'annotations/dev_pilot_1', prelabels_out=out / 'prelabels/dev_pilot_1')
            if not (store.out / 'annotations/annotation_progress.json').exists():
                store.export(len(pairs))
annotations = store.all()
mode_options = ['Blind', 'Review', 'Physical Identity Review']
if pilot_active and scope == 'DEV Pilot 0':
    mode_options.append('Disagreement Review')
mode = st.sidebar.radio('Mode', mode_options, index=1 if pilot_active else 0)
subset = st.sidebar.selectbox('Split', ['dev', 'frozen', 'all'])
filter_name = st.sidebar.selectbox('Filter', ['All', 'Unreviewed', 'Excluded', 'GPT/human disagreement', 'Review priority'])
priority_sort = st.sidebar.checkbox('Sort review priority first', value=pilot_active)
if mode == 'Disagreement Review':
    subset = 'dev'
    filter_name = 'GPT/human disagreement'
    st.sidebar.caption('DEV pilot label disagreements only')


def matches(p):
    a = annotations.get(p['item_id'])
    if subset != 'all' and p['split'] != subset:
        return False
    if filter_name == 'Unreviewed':
        return a is None
    if filter_name == 'Excluded':
        return bool(a and a['status'] == 'EXCLUDED')
    if filter_name == 'GPT/human disagreement':
        draft = store.prelabel(p['item_id'])
        return bool(a and a['status'] == 'REVIEWED' and draft and draft['valid'] and a['human_label'] != draft['parsed']['label'])
    if filter_name == 'Review priority':
        draft = store.prelabel(p['item_id'])
        return bool(draft and draft.get('needs_human_review'))
    return True


available = [p for p in pairs if matches(p)]
if priority_sort:
    available.sort(key=lambda p: (not bool((store.prelabel(p['item_id']) or {}).get('needs_human_review')), p['item_id']))
if not available:
    st.info('No items match this filter.')
    st.stop()
ids = [p['item_id'] for p in available]
resume = next((p['item_id'] for p in available if p['item_id'] not in annotations), ids[0])
if st.session_state.get('selected_item') not in ids:
    st.session_state['selected_item'] = resume


def navigate(delta):
    pos = ids.index(st.session_state['selected_item'])
    st.session_state['selected_item'] = ids[max(0, min(len(ids) - 1, pos + delta))]


nav = st.columns([1, 3, 1])
nav[0].button('Previous', on_click=navigate, args=(-1,), use_container_width=True)
with nav[1]:
    selected = st.selectbox('Item', ids, key='selected_item')
nav[2].button('Next', on_click=navigate, args=(1,), use_container_width=True)
pair = next(p for p in available if p['item_id'] == selected)
public = read(resolve(pair['evidence_package']['path']))
previous = annotations.get(selected, {})
if pilot_active:
    st.caption('DEV pilot only · all final labels still require human review; priority is sorting only.')
    entry = pilot_entries[selected]
    if entry['blind_first'] and mode == 'Review':
        blind_done = previous.get('human_blind_label') in {'SAME', 'DIFFERENT', 'AMBIGUOUS'}
        if not blind_done:
            st.info('Blind-first item: submit your own visual label before revealing GPT.')
            mode = 'Blind'
        elif not st.session_state.get('revealed_' + selected):
            if st.button('Reveal GPT prelabel'):
                st.session_state['revealed_' + selected] = True
                st.rerun()
            st.info('Blind annotation saved. GPT remains hidden until you choose Reveal.')
            mode = 'Blind'
st.subheader(f'Item {ids.index(selected) + 1} / {len(ids)} · {selected}')
st.caption(f"CASE_CHANGE_POLICY = {public['CASE_CHANGE_POLICY']} · {len(pairs)} total dataset items")
st.caption('Visual labels are drafts until human review. Similar model/color alone does not establish SAME.')


def display_side(side, title):
    st.header(title)
    crops = [i for i in public['images'] if i['side'] == side and i['kind'] == 'phone_crop']
    for offset in range(0, len(crops), 3):
        cols = st.columns(3)
        for col, image in zip(cols, crops[offset:offset + 3]):
            path = resolve(image['path'])
            with col:
                st.markdown(f"**[{image['image_id']}]**")
                try:
                    with Image.open(path) as im:
                        # Do not rescale tiny images in the main display.
                        st.image(im.copy(), width=min(im.width, 360))
                        st.caption(f'{im.width} × {im.height} original pixels')
                except OSError:
                    st.error('Missing/corrupt image; exclude with the matching reason.')
    contexts = [i for i in public['images'] if i['side'] == side and i['kind'] == 'context']
    with st.expander(f'{side} context images · orientation/visibility only'):
        for image in contexts:
            try:
                st.image(str(resolve(image['path'])), caption=f"[{image['image_id']}]", width=640)
            except Exception:
                st.error('Missing/corrupt context image')


cols = st.columns(2)
with cols[0]:
    display_side('Q', 'QUERY EPOCH')
with cols[1]:
    display_side('R', 'REFERENCE EPOCH')
with st.expander('Close inspection · original image / optional enlarged display'):
    image_id = st.selectbox('Image to inspect', [i['image_id'] for i in public['images']], key=f'inspect_{selected}')
    image = next(i for i in public['images'] if i['image_id'] == image_id)
    try:
        path = resolve(image['path'])
        im = Image.open(path)
        zoom = st.slider('Display magnification (adds no source detail)', 1, 4, 1)
        st.image(im, width=min(im.width * zoom, 1600))
        st.download_button('Download original image', path.read_bytes(), file_name=f'{selected}_{image_id}{path.suffix}')
    except OSError:
        st.error('Cannot inspect image')

if mode == 'Physical Identity Review':
    st.warning('Separate physical GT mode. These records are never included in GPT visual evidence.')
    inventory = {e['epoch_id']: e for e in read_lines(out / 'manifests/candidate_epoch_inventory.jsonl')}
    split = read(out / 'manifests/session_split.json')
    rec = next(r for r in split['recordings'] if r['video_id'] == pair['video_id'])
    with st.expander('Source video, timeline and experiment provenance'):
        st.video(str(resolve(rec['video_path'])))
        st.json({'recording': rec['video_id'], 'session': pair['session_id'],
                 'query': inventory[pair['query_epoch_id']], 'reference': inventory[pair['reference_epoch_id']]}, expanded=False)
    pg = store.all('physical').get(selected, {})
    physical = st.radio('Physical identity', ['SAME', 'DIFFERENT', 'UNKNOWN'],
                        index=['SAME', 'DIFFERENT', 'UNKNOWN'].index(pg.get('physical_identity', 'UNKNOWN')), horizontal=True)
    source = st.text_area('Physical identity source / experiment evidence', value=pg.get('physical_identity_source', ''))
    if st.button('Save physical GT', type='primary'):
        try:
            store.save_physical(selected, physical, source, len(pairs))
            st.success('Physical GT saved separately.')
        except ValueError as exc:
            st.error(str(exc))
    st.stop()

if mode == 'Disagreement Review':
    current_audit = pilot_audit(out)
    saved_flags = pilot_flags(out)
    disputed = {r['item_id']: r for r in current_audit['disagreements']}
    record = disputed[selected]
    st.subheader('GPT / human disagreement inspection')
    st.caption('Inspect the original Q/R crops and optional context above. Choose the error attribution yourself; no flag is inferred from the label mismatch.')
    st.json({'item_id': selected, 'gpt_label': record['gpt']['label'],
             'gpt_ambiguity_cause': record['gpt']['ambiguity_cause'],
             'gpt_challenge_tags': record['gpt']['challenge_tags'],
             'gpt_evidence_for_same': record['gpt']['evidence_for_same'],
             'gpt_evidence_for_different': record['gpt']['evidence_for_different'],
             'human_label': record['human']['human_label'],
             'human_challenge_tags': record['human'].get('human_challenge_tags', []),
             'human_note': record['human'].get('human_note', '')}, expanded=False)
    old_flag = saved_flags.get(selected, {'flag': 'UNREVIEWED', 'note': ''})
    flag = st.selectbox('Manual inspection flag', FLAGS,
                        index=FLAGS.index(old_flag['flag']), key='audit_flag_' + selected)
    flag_note = st.text_area('Inspection note (optional)', value=old_flag['note'], key='audit_note_' + selected)
    if st.button('Save inspection flag', type='primary'):
        try:
            save_flag(selected, flag, flag_note, out)
            render_report(out)
            st.success('Inspection flag saved; audit report updated.')
        except ValueError as exc:
            st.error(str(exc))
    st.caption(f"Current saved flag: {old_flag['flag']}")
    st.stop()

draft = None
if mode == 'Review':
    draft = store.prelabel(selected)
    if draft is None:
        st.info('No GPT prelabel exists. Human override remains available; no model is called by this UI.')
    else:
        st.subheader('GPT prelabel · separate from human gold')
        if draft['valid']:
            st.json(draft['parsed'])
        else:
            st.error('Invalid draft: ' + str(draft['validation_error']))
            st.code(draft['raw_text'])
        if draft['valid'] and st.button('Accept GPT', type='primary'):
            p = draft['parsed']
            store.save({'item_id': selected, 'status': 'REVIEWED', 'human_label': p['label'],
                'human_ambiguity_cause': p['ambiguity_cause'], 'human_challenge_tags': p['challenge_tags'],
                'accepted_gpt_prelabel': True, 'exclude_reason': None, 'annotation_mode': 'review_accept'}, len(pairs))
            st.success('Human final annotation saved. Raw GPT response preserved.')

key = f'{mode}_{selected}'
options = ['SAME', 'DIFFERENT', 'AMBIGUOUS', 'EXCLUDE ITEM']
initial = 'EXCLUDE ITEM' if previous.get('status') == 'EXCLUDED' else previous.get('human_label', 'AMBIGUOUS')
label = st.radio('Human decision' if mode == 'Blind' else 'Override decision', options,
                 index=options.index(initial), horizontal=True, key=key + '_label')
cause = None
reason = None
if label == 'AMBIGUOUS':
    choices = ['Select one cause'] + sorted(CAUSES)
    existing = previous.get('human_ambiguity_cause')
    cause = st.selectbox('Required ambiguity cause', choices, index=choices.index(existing) if existing in choices else 0, key=key + '_cause')
elif label == 'EXCLUDE ITEM':
    choices = ['Select one reason'] + EXCLUSIONS
    existing = previous.get('exclude_reason')
    reason = st.selectbox('Required exclusion reason', choices, index=choices.index(existing) if existing in choices else 0, key=key + '_reason')
st.markdown('**Challenge tags · independent from identity label**')
tag_cols = st.columns(3)
tags = []
for i, tag in enumerate(TAGS):
    if tag_cols[i % 3].checkbox(tag, value=tag in previous.get('human_challenge_tags', []), key=key + '_' + tag):
        tags.append(tag)
note = st.text_area('Optional human note', value=previous.get('human_note', ''), key=key + '_note')
if st.button('Save annotation' if mode == 'Blind' else 'Save override', type='primary', use_container_width=True):
    value = {'item_id': selected, 'status': 'EXCLUDED' if label == 'EXCLUDE ITEM' else 'REVIEWED',
             'human_label': None if label == 'EXCLUDE ITEM' else label,
             'human_ambiguity_cause': cause, 'human_challenge_tags': tags,
             'accepted_gpt_prelabel': False, 'exclude_reason': reason,
             'human_note': note, 'annotation_mode': mode.lower()}
    if mode == 'Blind':
        value.update(human_blind_label=value['human_label'], human_blind_ambiguity_cause=cause, human_blind_challenge_tags=tags)
    try:
        store.save(value, len(pairs))
        if pilot_active:
            st.rerun()
        st.success('Saved. You can return and edit this item; restart resumes at the first unreviewed item.')
    except ValueError as exc:
        st.error(str(exc))
st.sidebar.json(read(store.out / 'annotations/annotation_progress.json'))
