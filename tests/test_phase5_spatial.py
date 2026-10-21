"""Deterministic CPU contract tests; mock records are not physical GT."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
try:import jsonschema
except ImportError:sys.path.append(str(ROOT/"artifacts/pass_i/runtime/vendor"))
from memory_graph.integration.regions import validate_region,box_polygon
from memory_graph.integration.spatial import relate,associate_vlm,enrich_memory
from memory_graph.integration.pipeline import build_memory,search,decide
from memory_graph.scene_graph.models import TemporalMemory


def video():
    return dict(video_id="unseen_scene",source_sha256="mock-video-digest",time_base="1/30",width=100,height=100,
        frame_timeline=[dict(index=i,pts=i,source_time_s=i/30) for i in range(3)])


def region(frame=0):
    return dict(region_id="r"+str(frame),video_id="unseen_scene",source_video_sha256="mock-video-digest",
        source_frame_index=frame,source_time_s=frame/30,native_pts=frame,time_base="1/30",
        region_label="mock desk patch",region_category="desk",polygon=box_polygon([10,30,90,90]),
        geometry_kind="MOCK_POLYGON",valid_frame_indices=[frame],viewpoint_id="view"+str(frame),
        evidence_refs=["MOCK_REGION_NOT_REAL_GT"],grounding_status="CANDIDATE",surface_candidate=True,usable_surface=False)


def observation(frame=0,source="CV",identity=False):
    o=dict(observation_id="o"+str(frame)+source,video_id="unseen_scene",source_video_sha256="mock-video-digest",
        source=source,source_frame_indices=[frame],source_times_s=[frame/30],object_category="phone",
        object_description="mock phone",object_instance_candidate="candidate_mock",authorized_entity_id=None,
        identity_authorization=None,visibility="VISIBLE",bbox=[30,40,50,50],evidence_refs=["MOCK_OBJECT_NOT_REAL_GT"],
        provenance={},physical_state="UNKNOWN",physical_state_evidence=None,location_candidate=None)
    if identity:o.update(authorized_entity_id="mock-video-digest::phone_01",identity_authorization={"authorization_id":"mock"},authorization_validation="VERIFIED_FINAL_LEDGER_REPLAY")
    return o


def verified_region(frame=0):
    r=region(frame);r.update(grounding_status="VERIFIED",usable_surface=True,verification=dict(origin="INDEPENDENT_GEOMETRIC_MEASUREMENT",refs=["MOCK_REGION_MEASUREMENT"]))
    return r


def cue(o,r,state="RESTING_CONTACT"):
    return dict(origin="INDEPENDENT_CONTACT_MEASUREMENT",observation_id=o["observation_id"],region_id=r["region_id"],
        source_video_sha256=o["source_video_sha256"],source_frame_index=r["source_frame_index"],source_time_s=r["source_time_s"],state=state,refs=["MOCK_CONTACT_MEASUREMENT"])


class SpatialTests(unittest.TestCase):
    def test_native_frame_scope(self):
        r=region();self.assertEqual(validate_region(r,video()),r)
        r["native_pts"]=9
        with self.assertRaises(ValueError):validate_region(r,video())

    def test_no_unjustified_tracking(self):
        r=region();r["valid_frame_indices"]=[0,1]
        with self.assertRaises(ValueError):validate_region(r,video())
        self.assertEqual(relate(observation(1),region())["grounding_status"],"UNKNOWN")

    def test_overlap_not_support(self):
        result=relate(observation(),region())
        self.assertEqual(result["spatial_relation"],"POSSIBLY_ON_SURFACE")
        self.assertEqual(result["grounding_status"],"CANDIDATE")
        self.assertFalse(result["physical_support_verified"])

    def test_near_box_not_inside(self):
        r=region();r.update(region_label="box exterior",surface_candidate=False)
        o=observation();o["bbox"]=[92,40,98,50]
        result=relate(o,r)
        self.assertEqual(result["spatial_relation"],"NEAR_REGION")
        self.assertEqual(result["relation_scope"],"IMAGE_SPACE_ONLY")

    def test_distinct_projection_relations(self):
        r=region();r["surface_candidate"]=False
        for bbox,expected in [([30,40,50,50],"INSIDE_REGION"),([85,40,99,50],"OVERLAPS_REGION"),([30,20,50,28],"ABOVE_REGION"),([0,0,5,5],"UNKNOWN")]:
            o=observation();o["bbox"]=bbox
            self.assertEqual(relate(o,r)["spatial_relation"],expected)

    def test_held_above_contradicts_support(self):
        o=observation();r=region()
        self.assertEqual(relate(o,r,cue(o,r,"HELD_ABOVE"))["grounding_status"],"CONTRADICTED")

    def test_same_model_not_independent_support(self):
        o=observation();r=verified_region();c=cue(o,r);c["origin"]="VLM"
        self.assertEqual(relate(o,r,c)["grounding_status"],"CANDIDATE")

    def test_verified_requires_contact_and_region(self):
        o=observation(identity=True);r=region()
        self.assertEqual(relate(o,r,cue(o,r))["grounding_status"],"CANDIDATE")
        r=verified_region()
        self.assertEqual(relate(o,r,cue(o,r))["spatial_relation"],"ON_SURFACE")

    def test_category_does_not_bind(self):
        result=associate_vlm([observation(source="VLM"),observation(identity=True)])[0]
        self.assertEqual(result["status"],"UNRESOLVED")
        self.assertIsNone(result["persistent_entity_id"])
        self.assertEqual(len(result["candidate_observation_ids"]),1)

    def test_missing_cv_not_absence(self):
        a=associate_vlm([observation(source="VLM")])[0]
        self.assertEqual(a["reason"],"NO_CV_DETECTION_NOT_PROOF_OF_ABSENCE")

    def test_localized_unique_and_multiple_candidates(self):
        v=observation(source="VLM");v["localization"]={"coordinate_space":"SOURCE_PIXELS","bbox":v["bbox"],"evidence_refs":["MOCK_LOCALIZATION"]}
        c=observation(identity=True)
        self.assertEqual(associate_vlm([v,c])[0]["status"],"RESOLVED_LOCAL_OBSERVATION")
        c2=deepcopy(c);c2["observation_id"]="second"
        self.assertEqual(associate_vlm([v,c,c2])[0]["status"],"UNRESOLVED")

    def test_candidate_does_not_override_trusted(self):
        a,b=observation(identity=True),observation(1,identity=True)
        r,s=verified_region(),region(1)
        memory=build_memory("unseen_scene",[a,b],[],[],[])
        enrich_memory(memory,video(),[r,s],{(a["observation_id"],r["region_id"]):cue(a,r)})
        result=search(memory,"Where is my phone?")
        self.assertEqual(result["status"],"LAST_CONFIRMED_LOCATION")
        self.assertEqual(result["candidates"][0]["source_frame_index"],0)
        self.assertTrue(result["candidates"][0]["current_location_uncertain"])

    def test_search_ties_and_query_identity(self):
        a=observation();r=region();s=deepcopy(r);s["region_id"]="another_region"
        m=build_memory("unseen_scene",[a],[],[],[]);enrich_memory(m,video(),[r,s])
        result=search(m,"phone")
        self.assertEqual(result["status"],"POSSIBLE_LOCATIONS")
        self.assertTrue(all(c["ordering_unresolved_tie"] for c in result["candidates"]))
        self.assertEqual(search(m,"phone",entity_id="unknown_entity")["status"],"UNKNOWN")

    def test_visibility_and_disappearance_no_events(self):
        a=observation();a["visibility"]="UNKNOWN"
        m=build_memory("unseen_scene",[a],[],[],[]);enrich_memory(m,video(),[region()])
        self.assertEqual(search(m,"phone")["status"],"UNKNOWN")
        self.assertEqual(m.transitions,[])

    def test_persist_reload_new_id(self):
        a=observation();m=build_memory("unseen_scene",[a],[],[],[])
        enrich_memory(m,video(),[region()])
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"graph.json";p.write_text(m.model_dump_json(),encoding="utf8")
            restored=TemporalMemory.model_validate(json.loads(p.read_text()))
        self.assertEqual(search(m,"手機"),search(restored,"手機"))
        self.assertTrue(search(restored,"手機")["candidates"][0]["region_evidence_refs"])

    def test_region_cannot_self_assert_verified(self):
        r=region();r["grounding_status"]="VERIFIED"
        with self.assertRaises(ValueError):validate_region(r,video())

    def test_no_identity_from_unvalidated_flag(self):
        o=observation(identity=True);del o["authorization_validation"]
        self.assertIsNone(relate(o,region())["persistent_entity_id"])

    def test_later_held_invalidates_current_not_history(self):
        o=observation(identity=True);r=verified_region();held=observation(1,identity=True)
        held.update(physical_state="HELD_BY_PERSON",physical_state_evidence={"origin":"CV_MEASUREMENT","refs":["MOCK_HELD"]})
        m=build_memory("unseen_scene",[o,held],[],[],[])
        enrich_memory(m,video(),[r],{(o["observation_id"],r["region_id"]):cue(o,r)})
        result=search(m,"phone")
        self.assertTrue(result["candidates"][0]["prior_location_invalidated"])
        self.assertEqual(len(result["location_history"]),1)

    def test_other_movable_categories_are_queryable(self):
        o=observation();o["object_category"]="cup"
        m=build_memory("unseen_scene",[o],[],[],[]);enrich_memory(m,video(),[region()])
        self.assertEqual(search(m,"cup")["status"],"POSSIBLE_LOCATIONS")
        self.assertEqual(search(m,"phone")["status"],"UNKNOWN")

    def test_contact_wrong_frame_cannot_verify(self):
        o=observation(identity=True);r=verified_region();c=cue(o,r);c["source_frame_index"]=1
        self.assertEqual(relate(o,r,c)["grounding_status"],"CANDIDATE")

    def test_triangle_bbox_overlap_not_polygon_nearness(self):
        r=region();r.update(surface_candidate=False,polygon=[[10,10],[90,10],[10,90]])
        o=observation();o["bbox"]=[80,80,90,90]
        self.assertEqual(relate(o,r)["spatial_relation"],"UNKNOWN")

    def test_authorized_candidate_before_newer_unresolved(self):
        a,b=observation(identity=True),observation(1)
        m=build_memory("unseen_scene",[a,b],[],[],[]);enrich_memory(m,video(),[region(),region(1)])
        result=search(m,"phone")
        self.assertEqual(result["candidates"][0]["source_frame_index"],0)
        self.assertEqual(result["candidates"][0]["location_class"],"POSSIBLE_LOCATION")


if __name__=="__main__":unittest.main()
