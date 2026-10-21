"""CPU-only contracts with explicit mock coordinates, not localization GT."""
from copy import deepcopy
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
try:import jsonschema
except ImportError:sys.path.append(str(ROOT/"artifacts/pass_i/runtime/vendor"))
from test_phase5_spatial import observation,video,region,verified_region,cue
from memory_graph.integration.target_surface import pixels,parse,adapt_localization,integrate,query_result
from memory_graph.integration.pipeline import build_memory,search
from memory_graph.integration.spatial import enrich_memory,associate_vlm
from memory_graph.scene_graph.models import TemporalMemory


def frame():return dict(video_id="unseen_scene",source_video_sha256="mock-video-digest",source_frame_index=0,
    source_time_s=0,native_pts=0,time_base="1/30",width=100,height=100,sha256="mock-frame",path="mock.png")


def payload(kind="smartphone",state="HELD"):
    return dict(targets=[dict(id="obj1",kind=kind,bbox=[300,400,500,500],visible_state=state,description="mock object")],
        surfaces=[dict(id="surface1",kind="tabletop",polygon=[[100,300],[900,300],[900,900],[100,900]],description="mock top")])


class PerceptionTests(unittest.TestCase):
    def test_source_pixel_scaling(self):
        self.assertEqual(pixels([100,200,500,700],1280,720,box=True),[128.,144.,640.,504.])

    def test_wrong_source_rejected(self):
        f=frame();f["source_time_s"]=1
        with self.assertRaises(ValueError):adapt_localization(payload(),video(),f,"mock-raw",[])

    def test_bounds_and_nonconvex_rejected(self):
        with self.assertRaises(ValueError):pixels([-1,1,500,500],100,100,box=True)
        with self.assertRaises(ValueError):pixels([[0,0],[900,900],[900,0],[0,900]],100,100)

    def test_missing_not_negative(self):
        p,s=parse('{"targets":[],"surfaces":[]}')
        self.assertTrue(s["valid"])
        self.assertEqual(adapt_localization(p,video(),frame(),"mock",[])[0],[])
        p,s=parse('I cannot tell')
        self.assertIsNone(p);self.assertTrue(s["invalid_is_not_absence"])

    def test_held_not_surface_verified(self):
        base=build_memory("unseen_scene",[],[],[],[])
        mem=integrate(base,video(),[frame()],{0:dict(parsed=payload(),raw_ref="mock")})
        loc=mem.metadata["location_observations"][0]
        self.assertEqual(loc["grounding_status"],"CANDIDATE")
        self.assertNotIn(loc["spatial_relation"],{"ON_SURFACE","POSSIBLY_ON_SURFACE"})
        self.assertFalse(loc["state_claim_is_independent_support"])

    def test_surface_is_unverified(self):
        _,r,_,_,_=adapt_localization(payload(),video(),frame(),"mock",[])
        self.assertEqual(r[0]["surface_semantics"],"UNVERIFIED_SURFACE_CANDIDATE")
        self.assertFalse(r[0]["usable_surface"])

    def test_telephone_not_users_smartphone(self):
        base=build_memory("unseen_scene",[observation()],[],[],[])
        m=integrate(base,video(),[frame()],{0:dict(parsed=payload("desk_telephone"),raw_ref="mock")})
        self.assertEqual(search(m,"phone")["status"],"UNKNOWN")
        self.assertTrue(all(o["authorized_entity_id"] is None for o in m.metadata["target_localizations"]))

    def test_historical_claim_not_given_new_coordinates(self):
        old=observation(source="VLM")
        base=build_memory("unseen_scene",[old],[],[],[])
        m=integrate(base,video(),[frame()],{0:dict(parsed=payload(),raw_ref="mock")})
        association=next(a for a in m.metadata["vlm_cv_associations"] if a["vlm_observation_id"]==old["observation_id"])
        self.assertEqual(association["status"],"UNRESOLVED")
        self.assertNotIn("localization",old)

    def test_local_observation_match_does_not_authorize_identity(self):
        t,_,c,_,_=adapt_localization(payload(),video(),frame(),"mock",[])
        a=associate_vlm(t+c)[0]
        self.assertEqual(a["status"],"RESOLVED_LOCAL_OBSERVATION")
        self.assertIsNone(a["persistent_entity_id"])

    def test_existing_authorization_not_transferred_to_new_box(self):
        t,_,_,audit,_=adapt_localization(payload(),video(),frame(),"mock",[observation(identity=True)])
        self.assertIsNone(t[0]["authorized_entity_id"])
        self.assertFalse(audit[0]["identity_transferred"])

    def test_frame_local_new_video_reload_and_other_object(self):
        base=build_memory("unseen_scene",[],[],[],[])
        m=integrate(base,video(),[frame()],{0:dict(parsed=payload("requested_object"),raw_ref="mock",target_query="cup")})
        self.assertEqual(search(m,"cup"),search(TemporalMemory.model_validate_json(m.model_dump_json()),"cup"))
        self.assertEqual(search(m,"cup")["status"],"POSSIBLE_LOCATIONS")
        self.assertEqual(m.metadata["new_surface_regions"][0]["valid_frame_indices"],[0])

    def test_visible_without_region(self):
        base=build_memory("unseen_scene",[],[],[],[]);p=payload();p["surfaces"]=[]
        m=integrate(base,video(),[frame()],{0:dict(parsed=p,raw_ref="mock")})
        result=search(m,"phone")
        self.assertEqual(result["status"],"UNKNOWN")
        self.assertEqual(result["observation_status"],"LOCALIZED_OBJECT_WITHOUT_GROUNDED_REGION")

    def test_entity_search_cannot_leak_category_only_localizations(self):
        from memory_graph.integration.target_surface import query_result
        base=build_memory("unseen_scene",[],[],[],[])
        m=integrate(base,video(),[frame()],{0:dict(parsed=payload(),raw_ref="mock")})
        result=query_result(m,"phone",entity_id="enrolled_phone")
        self.assertEqual(result["search_scope"],"PERSISTENT_ENTITY")
        self.assertEqual(result["candidates"],[])
        self.assertEqual(result["localized_object_without_region"],[])

    def test_mask_must_match_source_frame_and_dimensions(self):
        refinement={"obj1":dict(accepted=True,source_frame_sha256="wrong",mask_rle={"shape":[100,100]},mask_ref={"sha256":"mock"})}
        with self.assertRaises(ValueError):adapt_localization(payload(),video(),frame(),"mock",[],refinements=refinement)
        refinement["obj1"]["source_frame_sha256"]="mock-frame"
        refinement["obj1"]["mask_rle"]["shape"]=[10,10]
        with self.assertRaises(ValueError):adapt_localization(payload(),video(),frame(),"mock",[],refinements=refinement)

    def test_verified_baseline_history_not_downgraded(self):
        o=observation(identity=True);r=verified_region()
        base=build_memory("unseen_scene",[o],[],[],[])
        enrich_memory(base,video(),[r],{(o["observation_id"],r["region_id"]):cue(o,r)})
        m=integrate(base,video(),[frame()],{0:dict(parsed=payload(state="UNKNOWN"),raw_ref="mock")})
        self.assertEqual(search(m,"phone")["status"],"LAST_CONFIRMED_LOCATION")
        self.assertEqual(m.metadata["trusted_location_history"],base.metadata["trusted_location_history"])

    def test_category_conflict_not_persistent_target(self):
        o=observation(identity=True);base=build_memory("unseen_scene",[o],[],[],[])
        m=integrate(base,video(),[frame()],{0:dict(parsed=payload("desk_telephone"),raw_ref="mock")})
        self.assertFalse(any(x.get("authorized_entity_id") for x in m.metadata["observations"]))
        self.assertTrue(o["authorized_entity_id"])

    def test_canvas_coordinate_contract_not_silent_clipping(self):
        import json
        p=payload();p["targets"][0]["bbox"]=[100,200,200,300];p["surfaces"]=[]
        parsed,status=parse(json.dumps(p),[1008,560])
        self.assertTrue(status["valid"])
        bbox=pixels(parsed["targets"][0]["bbox"],1280,720,box=True)
        self.assertAlmostEqual(bbox[0],100/1008*1280)
        self.assertAlmostEqual(bbox[1],200/560*720)
        p["targets"][0]["bbox"][3]=600
        parsed,status=parse(json.dumps(p),[1008,560])
        self.assertIsNone(parsed)

    def test_duplicate_surface_geometry_not_counted_twice(self):
        p=payload();second=deepcopy(p["surfaces"][0]);second.update(id="desk2",kind="desk_surface");p["surfaces"].append(second)
        _,r,_,_,_=adapt_localization(p,video(),frame(),"mock",[])
        self.assertEqual(len(r),1)


if __name__=="__main__":unittest.main()
