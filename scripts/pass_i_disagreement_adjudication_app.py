"""Standalone blind adjudication UI for six fixed Pilot 1 disagreements."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import streamlit as st
from PIL import Image

from memory_graph.pass_i.common import OUT, resolve
from memory_graph.pass_i.disagreement_adjudication import (
    ITEM_IDS, AdjudicationStore, cases, write_completed_report,
)

st.set_page_config(page_title='FindMind Pilot 1 Blind Adjudication', layout='wide')
out = Path(os.environ.get('FINDMIND_PASS_I_DATASET', OUT))
public_cases = cases(out)
store = AdjudicationStore(out)
saved = store.all()

st.title('Pilot 1 · Blinded visual adjudication')
st.caption(f"Completed {len(saved)}/{len(ITEM_IDS)}. Only the six fixed Q/R evidence pairs are shown. Earlier human and GPT judgments are hidden.")
st.info('SAME requires a persistent, distinctive feature visible on both sides. DIFFERENT requires positive physically incompatible evidence. Similar model, color, camera layout, size, or shape alone cannot prove SAME; a missing matching feature alone cannot prove DIFFERENT. Choose AMBIGUOUS when the physical instance cannot be justified.')

pending = st.session_state.pop('adj_pending_item', None)
if pending in ITEM_IDS:
    st.session_state['adj_selected_item'] = pending
if st.session_state.get('adj_selected_item') not in ITEM_IDS:
    st.session_state['adj_selected_item'] = next((item for item in ITEM_IDS if item not in saved), ITEM_IDS[0])

def navigate(delta):
    index = ITEM_IDS.index(st.session_state['adj_selected_item'])
    st.session_state['adj_selected_item'] = ITEM_IDS[max(0, min(len(ITEM_IDS)-1, index+delta))]

nav = st.columns([1, 4, 1])
nav[0].button('Previous', on_click=navigate, args=(-1,), use_container_width=True)
with nav[1]:
    selected = st.selectbox('Pair ID', ITEM_IDS, key='adj_selected_item')
nav[2].button('Next', on_click=navigate, args=(1,), use_container_width=True)
public = public_cases[selected]
previous = saved.get(selected, {})
st.subheader(selected)

def display(side):
    st.markdown(f'### {side} images')
    crops = [image for image in public['images'] if image['side'] == side]
    for image in crops:
        with Image.open(resolve(image['path'])) as im:
            st.markdown(f"**{image['image_id']}**")
            st.image(im.copy(), width=min(im.width, 400))
            st.caption(f'{im.width} × {im.height} source pixels')
    return [image['number'] for image in crops]

left, right = st.columns(2)
with left:
    q_available = display('Q')
with right:
    r_available = display('R')

choices = ['Select a decision', 'SAME', 'DIFFERENT', 'AMBIGUOUS']
old_label = previous.get('adjudicated_label')
label = st.selectbox('Your blinded decision', choices,
                     index=choices.index(old_label) if old_label in choices else 0,
                     key=f'adj_label_{selected}')
q_numbers, r_numbers = [], []
feature = ''
reason = ''
ack = False
if label in {'SAME', 'DIFFERENT'}:
    q_numbers = st.multiselect('Exact Q image number(s)', q_available,
                               default=previous.get('q_image_numbers', []), key=f'adj_q_{selected}')
    r_numbers = st.multiselect('Exact R image number(s)', r_available,
                               default=previous.get('r_image_numbers', []), key=f'adj_r_{selected}')
    feature = st.text_area('Specific visible physical feature(s)',
                           value=previous.get('visible_physical_feature', ''), key=f'adj_feature_{selected}',
                           help='Cite a scratch, crack, sticker, case damage, screen-protector defect, stain, or another persistent distinctive feature; for DIFFERENT, describe the positive incompatibility.')
    reason = st.text_area('Why this supports physical-instance identity or incompatibility',
                          value=previous.get('instance_identity_explanation', ''), key=f'adj_reason_{selected}',
                          help='Explain the cited Q/R comparison. Model, type, color, size, or shape similarity alone is insufficient for SAME; absence alone is insufficient for DIFFERENT.')
    ack_label = ('I identified a positive persistent instance-specific match in the cited Q/R images.' if label == 'SAME'
                 else 'I identified positive physically incompatible evidence in the cited Q/R images.')
    ack = st.checkbox(ack_label, key=f'adj_ack_{selected}_{label}')
elif label == 'AMBIGUOUS':
    reason = st.text_area('Optional reason the physical instance cannot be resolved',
                          value=previous.get('instance_identity_explanation', ''), key=f'adj_ambiguous_reason_{selected}')

save_col, next_col = st.columns(2)
save_clicked = save_col.button('Save adjudication', type='primary', use_container_width=True)
next_clicked = next_col.button('Save & Next', use_container_width=True)
if save_clicked or next_clicked:
    try:
        store.save(selected, label, q_numbers, r_numbers, feature, reason, ack, public)
        report = write_completed_report(out)
        if next_clicked:
            index = ITEM_IDS.index(selected)
            st.session_state['adj_pending_item'] = ITEM_IDS[min(len(ITEM_IDS)-1, index+1)]
            st.rerun()
        st.success('Separate blinded adjudication saved.' + (' All six are complete; report generated.' if report else ''))
    except ValueError as exc:
        st.error(str(exc))

if len(saved) == len(ITEM_IDS):
    st.caption('All six decisions have been saved. The comparison report is available in artifacts/pass_i/reports.')
