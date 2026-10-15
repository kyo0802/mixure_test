# Exploratory preregistration draft — UNAPPROVED

Objective: structured evidence-grounded local-target event feasibility, not population accuracy. Model identity/receipt sources as audited. Candidate full serialization components SHA256 `187f59fd1c85284c6ae33894f61761c24b82581687794a16cf3556772de653ff`; event-only SHA is distinct. All parameter choices below remain proposals. The existing video adapter lacks system parity and reference support; no corrected runtime is claimed.

{
  "status": "DRAFT_UNAPPROVED",
  "freeze_readiness": "PROTOCOL_NOT_READY_TO_FREEZE",
  "baseline": "QWEN25_VL_7B_INSTRUCT_NF4_BF16_SDPA",
  "revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
  "authority": {
    "dataset_path": "artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json",
    "dataset_sha256": "ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c",
    "dataset_receipt_sha256": "92c3516a6f4cec82e0b15096e0011631162c6343f0464f7470a9f348d4e0f489",
    "import_sha256": "3f85134d8c4f9f78e1b16bea3ec937225d37ff671e8caeb6620e401c3bb50a0b",
    "policy_sha256": "c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4",
    "phase2a_manifest_sha256": "1c423256cd31ea0e585b1bc3e57610fc8b215fcbe2757108db3bd96736af9e46",
    "identity_resolution_sha256": "07a6dae253e2060468b1153f4457cd475ae44ff4f7b5cd0f25db8ffa50747b5a",
    "exhaustiveness_sidecar_sha256": "fa0133e4e49e54bdbac2ba59420d29b504e8bf219fa8179b57cd1b35261a005c",
    "negative_readiness_sha256": "aa0f381c9a6f9d30bcce7c7074c77a7a77d443a3f8eaba3273208cb8fbc0aa15",
    "binding_causality_status": "CAUSALITY_UNVERIFIED"
  },
  "full_prompt_components_sha256": "187f59fd1c85284c6ae33894f61761c24b82581687794a16cf3556772de653ff",
  "sampling_recommendation": "UNIFORM_8",
  "target_reference": "UNRESOLVED_AWAITING_HUMAN_DECISION",
  "generation_recommendation": {
    "do_sample": false,
    "max_new_tokens": 1024,
    "generation_deadline_s": 300,
    "transport_deadline_s": 330,
    "load_deadline_s": 120
  },
  "repeat_recommendation": 1,
  "retry_generation": 0,
  "retry_transport_before_generation": 1,
  "matching_tolerance_s": {
    "candidate": 0.2,
    "approved": false,
    "rationale": "Fixed common prospective value from prior proposal; external task temporal tolerance not independently established; requires human decision"
  },
  "matching": "same ontology/type and designated local target; exact native time kept; bounded/uncertain bracket interval with no fabricated midpoint; one-to-one nearest time then stable prediction order; extra predictions in nonexhaustive windows UNEVALUATED; invalid citations INVALID_OUTPUT not NO_EVENT; duplicate predictions flagged and not additional matches; no subframe claims",
  "cohort": [
    {
      "opaque_id": "W_db55b29f820c2b3e3afb",
      "private_item_id": "PT2A_5dbb180e8ff88762",
      "stratum": "DESCRIPTIVE_UNCERTAINTY_ONLY"
    },
    {
      "opaque_id": "W_5597d9b003977e053d70",
      "private_item_id": "PT2A_9d15d2a6b56b56d0",
      "stratum": "STRICT_NEGATIVE_CASE_ALERT_ANALYSIS"
    },
    {
      "opaque_id": "W_ec4751640324779435e6",
      "private_item_id": "PT2A_b35d807b28b92101",
      "stratum": "STRICT_NEGATIVE_CASE_ALERT_ANALYSIS"
    },
    {
      "opaque_id": "W_b8a53fea6aa8b92dc94f",
      "private_item_id": "PT2A_c58b4df88a2f6801",
      "stratum": "KNOWN_EVENT_MATCHING_ONLY"
    },
    {
      "opaque_id": "W_f1d4f821d33515975293",
      "private_item_id": "PT2A_eb60192e6986cb4f",
      "stratum": "KNOWN_EVENT_MATCHING_ONLY"
    },
    {
      "opaque_id": "W_aef405003cc72cef0044",
      "private_item_id": "PT2A_fe0910d66f4c5614",
      "stratum": "STRICT_NEGATIVE_CASE_ALERT_ANALYSIS"
    }
  ],
  "run_order_candidate": [
    {
      "opaque_id": "W_5597d9b003977e053d70",
      "representation": "MULTI_IMAGE",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_b8a53fea6aa8b92dc94f",
      "representation": "REENCODED_AUTHORIZED_VIDEO",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_aef405003cc72cef0044",
      "representation": "STORYBOARD",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_b8a53fea6aa8b92dc94f",
      "representation": "STORYBOARD",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_f1d4f821d33515975293",
      "representation": "MULTI_IMAGE",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_aef405003cc72cef0044",
      "representation": "MULTI_IMAGE",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_db55b29f820c2b3e3afb",
      "representation": "MULTI_IMAGE",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_f1d4f821d33515975293",
      "representation": "STORYBOARD",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_5597d9b003977e053d70",
      "representation": "REENCODED_AUTHORIZED_VIDEO",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_ec4751640324779435e6",
      "representation": "STORYBOARD",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_f1d4f821d33515975293",
      "representation": "REENCODED_AUTHORIZED_VIDEO",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_ec4751640324779435e6",
      "representation": "REENCODED_AUTHORIZED_VIDEO",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_aef405003cc72cef0044",
      "representation": "REENCODED_AUTHORIZED_VIDEO",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_ec4751640324779435e6",
      "representation": "MULTI_IMAGE",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_5597d9b003977e053d70",
      "representation": "STORYBOARD",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_b8a53fea6aa8b92dc94f",
      "representation": "MULTI_IMAGE",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_db55b29f820c2b3e3afb",
      "representation": "REENCODED_AUTHORIZED_VIDEO",
      "reference": "UNRESOLVED",
      "repeat": 1
    },
    {
      "opaque_id": "W_db55b29f820c2b3e3afb",
      "representation": "STORYBOARD",
      "reference": "UNRESOLVED",
      "repeat": 1
    }
  ],
  "all_settings_approved": false,
  "capacity_verified": false,
  "prospective_denominators": {
    "known_positive_windows": 2,
    "strict_negative_case_windows": 3,
    "uncertainty_descriptive_windows": 1,
    "formal_benchmark": 0
  },
  "permitted": [
    "known supported event conditional matches",
    "negative case alerts",
    "schema and citation counts",
    "runtime success/failure",
    "uncertainty qualitative behavior"
  ],
  "forbidden_metrics": "accuracy/precision/recall/F1/hallucination_rate/significance/CI/superiority/generalization = UNDEFINED",
  "failure_policy": "preserve every raw output; explicit OOM/timeout_stage/JSON/schema/citation/unsupported; no fallback/reduction/repair; any changed parameter new version; no retry incorrect prediction",
  "separate_gates": [
    "complete protocol approval THEN future freeze",
    "separate RUN_PHASE2B_EXPLORATORY_PILOT after frozen receipt"
  ],
  "unresolved": [
    "reference authorization/localization symmetry",
    "video V2 formatting parity",
    "effective spatial cap vs declared max_pixels",
    "matching tolerance task justification",
    "matched-shape resource probe",
    "human complete approval"
  ]
}

Exact-time GT is native-frame exact, not physical subframe certainty; do not widen to BEFORE/AFTER envelope. Interval matching requires same type/target, model cited bounds within original conservative GT interval under approved rule; overlap and bound distances must be reported, and tolerance must not be grown until a hit appears. Common0.2s is unapproved and not justified by sparse gaps. Optional representation-specific sensitivity must be preregistered before outputs, reported separately, never selected post hoc. Sparse conditions may lack temporally resolving evidence; document this without changing GT.

Output1024 is a conservative schema allowance, not demonstrated sufficient: required schema can serialize multiple events/citations with rationales; a short179-token no-event smoke does not bound event count. Capture EOS explicitly in future instrumentation; distinguish deadline, cap exhaustion, complete JSON and EOS. Initial synthetic phases had code fences and deadlines, which remain failures. Greedy repeats, if later approved, test execution stability rather than independent stochastic samples.

Strict negatives are accepted V2 human windows but lack new full independent visual review (test1 only7/107 assistant spotcheck). Two positives non-exhaustive; extras UNEVALUATED. test8 no true negative claim. test3 no inputs. Fixed event-expected sample, no PLACEMENT or exhaustive positive, session independence unverified, CAUSALITY_UNVERIFIED, formal denominator0. No scoring ran here.
