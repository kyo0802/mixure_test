"""CPU-only contract fixtures, not physical-event ground truth."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.append(str(ROOT/"artifacts/pass_i/runtime/vendor"))
from memory_graph.integration.adapters import adapt_nemotron,adapt_cv,checked_frames,verified_guard_ledger,read,sha
from memory_graph.integration.pipeline import decide,run,search,persist


def fixture():
    video=dict(video_id="CPU_MOCK",source_sha256="mock",source_duration_s=3,
        frame_timeline=[dict(source_time_s=float(i)) for i in range(4)])
    frames=[dict(alias=f"F{i}",source_frame_index=i,native_pts_s=float(i)) for i in (0,1)]
    window=dict(video_id="CPU_MOCK",source_video_sha256="mock",window_id="ARBITRARY_NEW_WINDOW",frames=frames)
    raw=dict(status="EVENTS",observations=[dict(object="phone",states=[
        dict(frame="F0",state="ON_SURFACE"),dict(frame="F1",state="HELD_BY_PERSON")])],
        events=[dict(type="PICKUP",object="phone",before_frames=["F0"],after_frames=["F1"])])
    return video,window,raw


def normalize():
    v,w,r=fixture()
    return adapt_nemotron(json.dumps(r),w,v,"CPU_MOCK:raw")


def measured():
    obs,hyp,receipt=normalize()
    for i,o in enumerate(obs):
        o.update(source="CV",observation_id=f"measurement:{i}",authorized_entity_id="mock::e",
            identity_authorization={"fixture_only":True},authorization_validation="VERIFIED_FINAL_LEDGER_REPLAY",
            visibility="VISIBLE",physical_state_evidence={"origin":"CV_MEASUREMENT","refs":["CPU_MOCK:measured"]})
    return obs,hyp,receipt,{"before_observation_ids":[obs[0]["observation_id"]],
                          "after_observation_ids":[obs[1]["observation_id"]]}


def at_location(obs,name="desk"):
    obs["location_candidate"]=dict(id=name,origin="CV_SPATIAL_OBSERVATION",evidence_refs=["CPU_MOCK:zone"])


class IntegrationTests(unittest.TestCase):
    def test_future_entrypoint_and_no_class_identity(self):
        obs,hyp,r=normalize()
        self.assertTrue(r["validation"]["raw"]["full_valid"])
        self.assertTrue(all(o["authorized_entity_id"] is None for o in obs))
        self.assertEqual(decide(hyp[0],obs)["decision"],"UNCERTAIN")

    def test_invalid_not_no_event(self):
        v,w,_=fixture()
        obs,hyp,r=adapt_nemotron('{"status":',w,v,"CPU_MOCK:invalid")
        self.assertEqual((obs,hyp),([],[]))
        self.assertEqual(r["response_status"],"INVALID_OUTPUT")
        self.assertEqual(r["raw_output"],'{"status":')

    def test_raw_newlines_preserved(self):
        v,w,r=fixture()
        raw=json.dumps(r,indent=2).replace("\n","\r\n")
        _,_,receipt=adapt_nemotron(raw,w,v,"CPU_MOCK:crlf")
        self.assertEqual(receipt["raw_output"],raw)

    def test_fence_keeps_raw_invalid(self):
        v,w,r=fixture()
        o,h,r=adapt_nemotron("```json\n"+json.dumps(r)+"\n```",w,v,"CPU_MOCK:fence")
        self.assertFalse(r["validation"]["raw"]["full_valid"])
        self.assertEqual(len(h),1)
        self.assertNotEqual(decide(h[0],o)["decision"],"SUPPORTED")

    def test_alias_pts_bounds(self):
        v,w,_=fixture()
        for field,value in (("native_pts_s",.5),("source_frame_index",99),("alias","F0")):
            bad=copy.deepcopy(w);bad["frames"][1][field]=value
            with self.assertRaises(ValueError):checked_frames(bad,v)

    def test_held_to_held_is_not_pickup(self):
        v,w,r=fixture();r["observations"][0]["states"][0]["state"]="HELD_BY_PERSON"
        o,h,_=adapt_nemotron(json.dumps(r),w,v,"CPU_MOCK:held")
        self.assertEqual(decide(h[0],o)["decision"],"REJECTED")

    def test_contact_not_pickup(self):
        o,h,_,a=measured();o[1]["physical_state"]="ON_SURFACE"
        self.assertEqual(decide(h[0],o,a)["decision"],"REJECTED")

    def test_occlusion_not_placement(self):
        o,h,_,a=measured()
        h[0].update(type="PLACEMENT",before_claims=["HELD_BY_PERSON"],after_claims=["ON_SURFACE"])
        o[0]["physical_state"]="HELD_BY_PERSON";o[1].update(physical_state="UNKNOWN",visibility="NOT_VISIBLE")
        self.assertEqual(decide(h[0],o,a)["decision"],"UNCERTAIN")

    def test_no_independent_state_from_vlm_claim(self):
        o,h,_,a=measured()
        o[1]["physical_state_evidence"]["origin"]="VLM"
        self.assertEqual(decide(h[0],o,a)["decision"],"UNCERTAIN")

    def test_scoped_association_and_state_support(self):
        o,h,_,a=measured()
        self.assertEqual(decide(h[0],o,a)["decision"],"SUPPORTED")
        o[1]["source_times_s"]=[1.1]
        self.assertEqual(decide(h[0],o,a)["decision"],"UNCERTAIN")

    def test_unresolved_identity_even_with_transition(self):
        o,h,_,a=measured();o[1]["authorized_entity_id"]=None
        self.assertEqual(decide(h[0],o,a)["decision"],"UNCERTAIN")

    def test_uncertain_event_keeps_location_with_warning(self):
        o,h,r,_=measured();at_location(o[0])
        o[1]["physical_state_evidence"]=None
        memory=run("CPU_MOCK",o,h,[r])
        result=search(memory,"Where is my phone?")
        self.assertEqual(result["candidates"][0]["location"]["id"],"desk")
        self.assertTrue(result["candidates"][0]["event_ids"])
        self.assertEqual(memory.transitions,[])
        self.assertEqual(o[0]["location_candidate"]["id"],"desk")

    def test_supported_pickup_invalidates_current_location_not_history(self):
        o,h,r,a=measured();at_location(o[0])
        memory=run("CPU_MOCK",o,h,[r],{h[0]["hypothesis_id"]:a})
        self.assertEqual(search(memory,"phone")["status"],"UNKNOWN")
        self.assertEqual(memory.metadata["observations"][0]["location_candidate"]["id"],"desk")
        self.assertIsNone(memory.transitions[0]["location"])

    def test_rejected_does_not_overwrite_location(self):
        o,h,r,a=measured();at_location(o[0]);o[1]["physical_state"]="ON_SURFACE"
        memory=run("CPU_MOCK",o,h,[r],{h[0]["hypothesis_id"]:a})
        result=search(memory,"e")
        self.assertEqual(result["candidates"][0]["supporting_observation_ids"],["measurement:0"])
        self.assertEqual(memory.transitions,[])

    def test_same_exact_event_deduplicated(self):
        o,h,r,a=measured();second=copy.deepcopy(h[0]);second["hypothesis_id"]="other-window"
        memory=run("CPU_MOCK",o,[h[0],second],[r],{h[0]["hypothesis_id"]:a,"other-window":a})
        self.assertEqual(len(memory.events),2)
        self.assertEqual(len(memory.transitions),1)

    def test_overlap_alone_not_merge(self):
        o,h,r=normalize();second=copy.deepcopy(h[0]);second["hypothesis_id"]="different"
        second["before_refs"]=[dict(source_frame_index=2,native_pts_s=.1)]
        second["after_refs"]=[dict(source_frame_index=3,native_pts_s=.9)]
        second["native_interval_s"]=[.1,.9]
        memory=run("CPU_MOCK",o,[h[0],second],[r])
        self.assertEqual(memory.metadata["candidate_groupings"],[])
        self.assertEqual(memory.transitions,[])

    def test_unknown_surface_is_not_table(self):
        o,h,r=normalize()
        memory=run("CPU_MOCK",o,h,[r])
        result=search(memory,"phone")
        self.assertEqual(result["status"],"UNKNOWN")
        self.assertEqual(result["last_useful_observation"]["evidence_refs"][0],"CPU_MOCK:raw")

    def test_real_output_and_guard_ledger(self):
        exp=ROOT/"artifacts/pass_t/phase3/three_vlm_full_v1"
        result=read(exp/"model_results.json")["nemotron"]["rows"][0]
        window=next(w for w in read(exp/"dataset.json")["windows"] if w["window_id"]==result["window_id"])
        video=next(v for v in read(ROOT/"tools/findmind-gt-annotator/manifest.json")["videos"] if v["video_id"]==window["video_id"])
        raw=ROOT/result["raw_path"]
        self.assertEqual(sha(raw),result["raw_sha256"])
        obs,hyp,receipt=adapt_nemotron(raw.read_text(encoding="utf-8"),window,video,str(raw),ROOT)
        self.assertEqual(receipt["validation"]["raw"]["full_valid"],result["validation"]["raw"]["full_valid"])
        self.assertGreater(len(obs),0)
        folder=ROOT/"outputs/identity_rebuild/development/runs_final"/video["video_id"]
        snapshot=read(folder/"identity.json")
        self.assertGreater(len(verified_guard_ledger(snapshot)),0)
        revoked=copy.deepcopy(snapshot)
        for alias in revoked["aliases"]:alias["status"]="REVOKED"
        self.assertEqual(verified_guard_ledger(revoked),{})

    def test_production_persistence_rejected(self):
        o,h,r=normalize();memory=run("CPU_MOCK",o,h,[r])
        with self.assertRaises(PermissionError):persist(memory,ROOT/"production_graph.json")

    def test_placement_requires_actual_location(self):
        o,h,r,a=measured()
        h[0].update(type="PLACEMENT",before_claims=["HELD_BY_PERSON"],after_claims=["ON_SURFACE"])
        o[0]["physical_state"]="HELD_BY_PERSON";o[1]["physical_state"]="ON_SURFACE"
        memory=run("CPU_MOCK",o,h,[r],{h[0]["hypothesis_id"]:a})
        self.assertIsNone(memory.transitions[0]["location"])
        at_location(o[1],"CPU_MOCK:shelf")
        memory=run("CPU_MOCK",o,h,[r],{h[0]["hypothesis_id"]:a})
        self.assertEqual(memory.transitions[0]["location"]["id"],"CPU_MOCK:shelf")
        self.assertEqual(search(memory,"phone")["candidates"][0]["location"]["id"],"CPU_MOCK:shelf")

    def test_later_location_supersedes_only_same_entity(self):
        o,_,r,_=measured();o[0]["physical_state"]=o[1]["physical_state"]="ON_SURFACE"
        at_location(o[0],"first");at_location(o[1],"second")
        memory=run("CPU_MOCK",o,[],[r])
        self.assertEqual([c["location"]["id"] for c in search(memory,"phone")["candidates"]],["second"])
        o[1]["authorized_entity_id"]="mock::other"
        memory=run("CPU_MOCK",o,[],[r])
        self.assertEqual([c["location"]["id"] for c in search(memory,"phone")["candidates"]],["second","first"])

    def test_overlapping_supported_candidates_not_double_promoted(self):
        o,h,r,a=measured()
        extra=copy.deepcopy(o[1]);extra.update(observation_id="measurement:2",source_frame_indices=[2],source_times_s=[2.])
        second=copy.deepcopy(h[0]);second.update(hypothesis_id="second",
            after_refs=[dict(source_frame_index=2,native_pts_s=2.)],native_interval_s=[0.,2.])
        memory=run("CPU_MOCK",o+[extra],[h[0],second],[r],{
            h[0]["hypothesis_id"]:a,"second":{"before_observation_ids":["measurement:0"],"after_observation_ids":["measurement:2"]}})
        self.assertEqual(memory.transitions,[])
        self.assertTrue(all(e["decision"]=="UNCERTAIN" for e in memory.events))


if __name__=="__main__":unittest.main()
