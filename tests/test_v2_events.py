from memory_graph.config_v2 import EventConfig, KeyframeConfig
from memory_graph.events.event_proposer import propose_events, merge_events
from memory_graph.events.keyframe_selector import select_keyframes, score_candidates
from v2_helpers import timelines, event


def test_approaching_tracks_propose_proximity():
    tracks, _ = timelines([[(5+i*12,30) for i in range(6)],[(85,30)]*6])
    events = propose_events(tracks,6,EventConfig())
    assert any(e.event_type == 'proximity_change' for e in events)


def test_sustained_absence_is_candidate_not_lost():
    tracks,_ = timelines([[(10,20)]*5])
    events = propose_events(tracks,6,EventConfig())
    disappears = [e for e in events if e.event_type == 'disappearance_candidate']
    assert len(disappears) == 1 and disappears[0].peak_time == 2.6


def test_end_of_video_is_not_disappearance():
    tracks,_ = timelines([[(10,20)]*5])
    assert not any(e.event_type == 'disappearance_candidate' for e in propose_events(tracks,1.7,EventConfig()))


def test_motion_coupling_requires_persistent_nonzero_motion():
    tracks,_ = timelines([[(10+i*3,20) for i in range(6)],[(25+i*3,20) for i in range(6)]],['person','cup'])
    assert any(e.event_type == 'motion_coupling_candidate' for e in propose_events(tracks,6,EventConfig()))
    static,_ = timelines([[(10,20)]*6,[(25,20)]*6],['person','cup'])
    assert not any(e.event_type == 'motion_coupling_candidate' for e in propose_events(static,6,EventConfig()))


def test_overlapping_signals_merge_without_entire_video_chain():
    a,b,c = event(start=1,peak=1.5,end=2),event(ids=(2,3),start=1.8,peak=2,end=2.3),event(ids=(3,4),start=2.2,peak=2.4,end=2.8)
    a.signals=['proximity_change'];b.signals=['motion_coupling_candidate'];c.signals=['disappearance_candidate']
    merged = merge_events([a,b,c],EventConfig())
    assert len(merged)==1 and merged[0].involved_track_ids == [1,2,3,4]
    assert len(merged[0].signals)==3
    assert len(merge_events([a,event(start=9,peak=9.5,end=10)],EventConfig()))==2


def test_event_budget_is_enforced():
    events = [event(ids=(i+1,),start=i*3,peak=i*3+.5,end=i*3+1) for i in range(5)]
    assert sum(e.selected for e in merge_events(events,EventConfig(max_vlm_events=2)))==2


def test_keyframes_are_ordered_and_absence_is_retained():
    tracks,meta = timelines([[(10,20)]*5])
    chosen=select_keyframes(event(ids=(1,),peak=1.2),meta.sampled_frames,score_candidates(meta.sampled_frames,tracks),
        {},meta.duration,EventConfig(),KeyframeConfig(search_radius_seconds=0))
    assert [f.phase for f in chosen]==['before','during','after']
    assert chosen[0].timestamp < chosen[1].timestamp < chosen[2].timestamp
    assert abs(chosen[0].timestamp-.2)<1e-8 and abs(chosen[2].timestamp-2.2)<1e-8


def test_single_observation_noise_has_no_events():
    tracks,_=timelines([[(10,20)]])
    assert propose_events(tracks,6,EventConfig())==[]
