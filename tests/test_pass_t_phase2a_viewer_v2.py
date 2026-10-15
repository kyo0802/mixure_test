"""Actual Tk widget checks with isolated synthetic evidence, no production human answers."""
from types import SimpleNamespace
import tkinter as tk
import pytest
from test_pass_t_phase2a_v2 import synthetic, event
from memory_graph.pass_t.phase2a_v2 import viewer, policy


@pytest.fixture
def app(synthetic, tk_root):
    root = tk.Toplevel(tk_root); root.withdraw()
    instance = viewer.Viewer(root, synthetic['out'])
    root.update_idletasks(); root.update()
    yield instance
    instance.stop_play(); root.destroy()


@pytest.fixture(scope='module')
def tk_root():
    root = tk.Tk(); root.withdraw()
    yield root
    root.destroy()


def test_gui_starts_blank_unchecked_and_selected_only(app):
    assert app.form.controls['window_outcome'].get() == ''
    assert app.form.controls['last_confirmed_state'].get() == ''
    assert app.exhaustiveness.get() == ''
    assert all(not var.get() for var in app.exhaust_checks)
    assert all(not var.get() for var in app.attests.values())
    assert app.overlay.get() == 'SELECTED_CANDIDATE_ONLY'
    assert app.marker is None
    assert app.draft()['events'] == []
    assert app.feedback.winfo_manager()=='grid'
    assert app.evidence_scroll.cget('yscrollcommand')


def test_full_resolution_view_stays_on_same_authorized_frame(app):
    before=app.current()['frame_id']
    seen=[]
    def inspect_dialog():
        for window in app.root.winfo_children():
            if isinstance(window,tk.Toplevel):
                seen.append(window.title())
                window.destroy()
    app.root.after(20,inspect_dialog)
    app.inspect_current()
    assert app.current()['frame_id']==before
    assert any(before in title for title in seen)


@pytest.mark.parametrize('outcome', ['NO_CONFIRMED_EVENT','INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE'])
def test_outcome_change_removes_stale_completeness(app,outcome):
    app.form.controls['window_outcome'].set('CONFIRMED_EVENTS')
    app.exhaustiveness.set('EXHAUSTIVE_ATTESTED')
    for var in app.exhaust_checks: var.set(True)
    app.form.controls['window_outcome'].set(outcome)
    value=app.draft()
    assert 'event_list_exhaustiveness' not in value
    assert 'event_list_exhaustiveness_attestation' not in value
    assert all(not var.get() for var in app.exhaust_checks)


def test_non_exhaustive_never_serializes_attestation(app):
    app.form.controls['window_outcome'].set('CONFIRMED_EVENTS')
    app.exhaustiveness.set('NOT_ATTESTED')
    for var in app.exhaust_checks: var.set(True)
    assert 'event_list_exhaustiveness_attestation' not in app.draft()


def test_frame_navigation_uses_native_table(app):
    app.frame_step(1)
    assert app.current()['frame_id']=='S000011'
    assert '1.100000000' in app.time_label.cget('text')
    app.frame_step(100)
    assert app.current()['frame_id']=='S000015'
    app.frame_step(-100)
    assert app.current()['frame_id']=='S000010'


def test_human_citation_uses_current_frame_and_selected_observation(app):
    app.cite_kind.set('CANDIDATE_OBSERVATION_BACKED'); app.association.set('SUPPORTED')
    app.add_citation('BEFORE')
    assert app.pool[0]['frame_id']=='S000010'
    assert app.pool[0]['source_observation_ids']==['raw:0@10']
    app.frame_step(1); app.cite_kind.set('DIRECT_VISUAL_ONLY')
    app.cite_description.insert(0,'Synthetic visible target at center.')
    app.add_citation('AFTER')
    assert app.pool[1]['source_observation_ids']==[]
    assert app.pool[1]['source_timestamp_s']==1.1


def test_overlay_exposure_is_logged(app):
    app.overlay.set('ALL_CANDIDATES'); app.overlay_changed()
    assert app.draft()['interaction_metadata']['overlay_toggles'][0]['mode']=='ALL_CANDIDATES'
    app.overlay.set('OFF'); app.overlay_changed()
    assert len(app.logs)==2


@pytest.mark.parametrize('kind', ['POINT','BBOX'])
def test_manual_marker_converts_display_coordinates(app,kind):
    app.mark_mode.set(kind)
    start=SimpleNamespace(x=int(app.offset[0]+100*app.scale), y=int(app.offset[1]+100*app.scale))
    end=SimpleNamespace(x=int(app.offset[0]+200*app.scale), y=int(app.offset[1]+200*app.scale))
    app.mark_start(start); app.mark_end(end)
    assert app.marker['origin']=='GUI_DRAWN'
    assert app.marker['kind']==kind
    assert app.marker['frame_id']=='S000010'
    assert abs(app.marker['coordinates'][-1]-200)<2
    app.clear_marker(); assert app.marker is None


def test_event_form_preserves_multiple_citations_and_native_bounds(app):
    old=event(app.item)
    form=viewer.Form(app.root,app.schema['$defs']['event'],app,old,context='event')
    result=form.value()
    assert result['event_type']=='PICKUP'
    assert len(result['evidence'])==2
    assert result['event_time']['start_timestamp_s']==1.0
    assert result['event_time']['end_timestamp_s']==1.2
    form.destroy()


def test_preview_invalid_blank_form_cannot_submit(app):
    assert app.preview()['valid'] is False
    assert not list((app.out/'responses').glob('*.json'))


def test_structured_ui_valid_unknown_submission_and_resume(app, monkeypatch):
    controls=app.form.controls
    for key,value in {'reviewer_id':'SYNTHETIC_REVIEWER','window_outcome':'INSUFFICIENT_EVIDENCE',
                      'coverage_assessment':'UNKNOWN','last_confirmed_state':'STATE_UNKNOWN',
                      'unknown_or_unobserved_afterward':'是','subsequent_location':'UNKNOWN',
                      'target_identification_event_dependence':'UNKNOWN',
                      'target_identification_event_dependence_rationale':'Synthetic uncertainty.',
                      'target_recognition_used_pre_window_reference':'否','confidence':'UNKNOWN',
                      'human_rationale':'Synthetic only; insufficient evidence.'}.items():
        controls[key].set(value)
    controls['uncertainty'].controls['status'].set('UNKNOWN')
    controls['uncertainty'].controls['description'].set('Synthetic unknown.')
    controls['visibility_at_window_end'].controls['visibility'].set('VISIBILITY_UNKNOWN')
    controls['visibility_at_window_end'].controls['rationale'].set('Synthetic unknown visibility.')
    app.attests['human_attestation'].set(True)
    assert app.preview()['valid']
    monkeypatch.setattr(viewer.messagebox,'askyesno',lambda *args:True)
    app.save()
    assert len(list((app.out/'responses').glob('*.json')))==1
    app.load()
    assert str(app.save_button.cget('state'))=='disabled'
    assert app.form.controls['window_outcome'].get()==''
    assert app.draft()['events']==[]


@pytest.mark.parametrize('x,y', [(-1,0),(1280,0),(0,720)])
def test_letterbox_out_of_image_rejected(x,y):
    with pytest.raises(ValueError): viewer.display_to_source(x,y,1,(0,0))


def test_rounded_image_dimensions_use_actual_axis_scales():
    x,y=viewer.display_to_source(110,90,(0.5,0.4),(10,10))
    assert (x,y)==(200,200)


def test_blind_repeat_ui_has_no_first_answers(app,synthetic):
    from memory_graph.pass_t.phase2a_v2.storage import submit
    submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    root=tk.Toplevel(app.root); root.withdraw()
    repeat=viewer.Viewer(root,synthetic['out'],2)
    assert repeat.form.controls['window_outcome'].get()==''
    assert repeat.form.controls['last_confirmed_state'].get()==''
    assert set(repeat.linkage)=={'sha256','timestamp','reviewer_id'}
    assert repeat.draft()['events']==[]
    repeat.stop_play(); root.destroy()
