"""Streamlit presentation for human-only DEV CandidateEpoch evidence QC."""
from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import streamlit as st
from PIL import Image, ImageDraw

from memory_graph.pass_i.common import OUT, read, read_lines, resolve, sha
from memory_graph.pass_i.evidence_qc import CROP_STATES, EPOCH_STATES, QCStore, report


def _source_overlay(video_path: Path, observation: dict):
    cap = cv2.VideoCapture(str(video_path))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, observation['frame'])
        ok, bgr = cap.read()
    finally:
        cap.release()
    if not ok:
        raise OSError(f"Cannot decode source frame {observation['frame']}")
    if hashlib.sha256(bgr.tobytes()).hexdigest() != observation['raw_image_sha256']:
        raise ValueError('Source frame does not match original V297 inventory pixels')
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb)
    draw = ImageDraw.Draw(im)
    x1, y1, x2, y2 = observation['bbox']
    draw.rectangle((x1, y1, x2, y2), outline='#ff3030', width=max(2, im.width // 350))
    draw.text((max(0, x1), max(0, y1 - 18)), f"frame {observation['frame']} · {observation['observation_id']}", fill='#ff3030')
    return im


def render(out: Path = OUT):
    out = Path(out)
    store = QCStore(out)
    queue = store.queue['items']
    reviews = store.all()
    inventory = {e['epoch_id']: e for e in read_lines(out / 'manifests/candidate_epoch_inventory.jsonl') if e['split'] == 'dev'}
    recordings = {r['video_id']: r for r in read(out / 'manifests/session_split.json')['recordings'] if r['split'] == 'dev'}
    st.title('FindMind Pass I · Evidence QC')
    st.caption('Human-only review of DEV CandidateEpochs. Red boxes show the original detection/tracking bbox and are never sent to GPT.')
    filter_name = st.sidebar.selectbox('Evidence QC filter',
                                        ['All', 'Unreviewed only', 'VALID only', 'MIXED only', 'NO_USABLE_TARGET only'])
    def match(entry):
        state = reviews.get(entry['epoch_id'], {}).get('epoch_state')
        return (filter_name == 'All' or
                filter_name == 'Unreviewed only' and state is None or
                filter_name == 'VALID only' and state == 'VALID' or
                filter_name == 'MIXED only' and state == 'MIXED_IDENTITY' or
                filter_name == 'NO_USABLE_TARGET only' and state == 'NO_USABLE_TARGET')
    available = [entry for entry in queue if match(entry)]
    counts = {state: sum(r['epoch_state'] == state for r in reviews.values()) for state in EPOCH_STATES}
    st.sidebar.write(f"Reviewed {len(reviews)}/{len(queue)} · VALID {counts['VALID']} · MIXED {counts['MIXED_IDENTITY']} · NO_USABLE {counts['NO_USABLE_TARGET']}")
    if not available:
        st.info('No CandidateEpochs match this filter.')
        return
    ids = [e['epoch_id'] for e in available]
    resume = next((eid for eid in ids if eid not in reviews), ids[0])
    pending = st.session_state.pop('qc_pending_epoch', None)
    if pending in ids:
        st.session_state['qc_selected_epoch'] = pending
    if st.session_state.get('qc_selected_epoch') not in ids:
        st.session_state['qc_selected_epoch'] = resume
    def navigate(delta):
        position = ids.index(st.session_state['qc_selected_epoch'])
        st.session_state['qc_selected_epoch'] = ids[max(0, min(len(ids) - 1, position + delta))]
    cols = st.columns([1, 4, 1])
    cols[0].button('Previous', on_click=navigate, args=(-1,), use_container_width=True)
    with cols[1]:
        selected = st.selectbox('CandidateEpoch', ids, key='qc_selected_epoch')
    cols[2].button('Next', on_click=navigate, args=(1,), use_container_width=True)
    epoch = inventory[selected]
    previous = reviews.get(selected, {})
    chosen = epoch['clean_crops']
    observations = {o['observation_id']: o for o in epoch['source_observations']}
    rec = recordings[epoch['video_id']]
    video_path = resolve(rec['video_path'])
    st.subheader(f"{selected} · {epoch['video_id']} · {epoch['session_id']}")
    st.caption(f"Source frames {epoch['start_frame']}–{epoch['end_frame']} · selected crops {len(chosen)} · all source observations {len(observations)}")
    states = {}
    for number, crop in enumerate(chosen, 1):
        observation = observations[crop['observation_id']]
        st.markdown(f"### Crop {number} · frame {crop['frame']} · {crop['observation_id']}")
        left, right = st.columns([2, 1])
        with left:
            try:
                st.image(_source_overlay(video_path, observation), caption='Original source frame with detection/tracking bbox · human QC only', use_container_width=True)
            except (OSError, ValueError) as exc:
                st.error(str(exc))
        with right:
            path = resolve(observation['raw_crop_path'])
            if not path.is_file() or sha(path) != observation['raw_crop_sha256']:
                st.error('Original crop missing or SHA-256 mismatch')
            else:
                try:
                    with Image.open(path) as im:
                        st.image(im.copy(), width=min(im.width, 360), caption=f'Original crop {im.width}×{im.height} px')
                except OSError:
                    st.error('Original crop cannot be decoded')
            st.caption(f"Crop path: {observation['raw_crop_path']}")
            old = previous.get('crop_states', {}).get(crop['observation_id'])
            options = ['Select QC state'] + list(CROP_STATES)
            state = st.selectbox(f'Crop {number} QC state', options,
                                 index=options.index(old) if old in options else 0,
                                 key=f'qc_crop_{selected}_{crop["observation_id"]}')
            states[crop['observation_id']] = state
    st.markdown('### CandidateEpoch QC')
    st.caption('VALID requires at least one verified target crop and no unresolved mixed identity. KEEP_WEAK remains valid evidence.')
    options = ['Select epoch state'] + list(EPOCH_STATES)
    prior_state = previous.get('epoch_state')
    epoch_state = st.selectbox('Epoch QC state', options, index=options.index(prior_state) if prior_state in options else 0,
                               key=f'qc_epoch_state_{selected}')
    note = st.text_area('Human QC note (optional)', value=previous.get('human_note', ''), key=f'qc_note_{selected}')
    save, save_next = st.columns(2)
    clicked_save = save.button('Save', type='primary', use_container_width=True)
    clicked_next = save_next.button('Save & Next', use_container_width=True)
    if clicked_save or clicked_next:
        if 'Select QC state' in states.values() or epoch_state == 'Select epoch state':
            st.error('Assign exactly one state to every crop and the CandidateEpoch before saving.')
        else:
            try:
                store.save(selected, states, epoch_state, note)
                report(out)
                if clicked_next:
                    position = ids.index(selected)
                    st.session_state['qc_pending_epoch'] = ids[min(len(ids) - 1, position + 1)]
                    st.rerun()
                st.success('Human Evidence QC saved.')
            except ValueError as exc:
                st.error(str(exc))
    if len(observations) > len(chosen):
        with st.expander('Other source observations in this CandidateEpoch · human contamination check'):
            st.caption('These observations are not in the existing selected evidence. Inspect them when deciding MIXED_IDENTITY.')
            for observation in epoch['source_observations']:
                if observation['observation_id'] in states:
                    continue
                st.caption(f"frame {observation['frame']} · {observation['observation_id']}")
                try:
                    st.image(_source_overlay(video_path, observation), width=640)
                except (OSError, ValueError) as exc:
                    st.error(str(exc))
