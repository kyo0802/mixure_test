# V1 → V2 differences — prospective minimal amendment

V1 stays unapproved and byte-for-byte unchanged, including its receipt, report, tests and synthetic artifacts. V2 has an independent receipt and approval gate; no response migration, Stage B implementation, GT annotation or inference is performed. V2 policy is standalone, derived from the exact verified V1 policy rather than editing it.

## Policy differences

| Area | V1 | V2 |
|---|---|---|
| CONFIRMED_EVENTS completeness | Positive events supported, list explicitly not guaranteed exhaustive | Required event_list_exhaustiveness: EXHAUSTIVE_ATTESTED / NOT_ATTESTED / UNKNOWN |
| Explicit completeness attestation | None | Only EXHAUSTIVE_ATTESTED requires four separately affirmed statements: entire window reviewed, all confirmable target PICKUP/PLACEMENT annotated, no unresolved visibility/association/temporal gap could conceal more events, only the two-event ontology covered |
| Confirmed-window coverage | No full-window completeness gate | Exhaustive confirmed requires existing THROUGHOUT_ASSESSABLE plus supported first/middle/last COVERAGE citations and frame IDs; citations are not proof of continuous assessability |
| Hidden-event gaps | Can coexist with supported listed events | They prohibit exhaustive status; supported events remain NOT_ATTESTED/UNKNOWN with explicit existing uncertainty |
| Non-exhaustive window uncertainty | Generic required uncertainty fields | Completeness uncertainty cannot claim NO_ADDITIONAL_UNCERTAINTY; use OTHER_UNCERTAINTY / TIMING_UNCERTAIN / UNKNOWN and a description. Event-specific uncertainty unchanged |
| Strict NO_CONFIRMED_EVENT | Full assessability, coverage, negative-event human declaration | Unchanged; no new redundant completeness or negative-attestation field |
| INSUFFICIENT_EVIDENCE / TARGET_NOT_OBSERVABLE | No established transitions | Unchanged; no completeness claim; new fields absent |
| Full-window evaluation evidence | No exhaustive confirmed list guaranteed | Only validated exhaustive-confirmed/strict-no-event windows, subject to every inherited DEV/association/leakage gate. Primary additionally NOT_DEPENDENT |
| Unlisted events in NOT_ATTESTED/UNKNOWN | No completeness guarantee | Explicitly unevaluated, never exhaustive negatives or automatically FP/hallucination; supported positives allowed for separately reported exploratory matching/qualitative analysis |
| Causality/Phase1c/formal eligibility | Original strata/exclusions remain | Unchanged; completeness cannot override them or promote formal eligibility |
| GUI specification | General manual event controls | Add confirmed-only selector/no default, four unchecked controls, coverage/gap gate, explicit uncertainty and no stale fields |
| Semantic validator specification | Existing membership/state/chronology/eligibility rules | Add conditional completeness/attestation/coverage/gap consistency and inherited-gate-before-evaluation checks |
| Finalize specification | Validated outcomes and DEV export | Add completeness basis, full-window support/primary eligibility/exclusion reasons and separate non-exhaustive-positive reporting; no metrics now |
| Future test specification | V1 categories | Keep all V1 categories and add completeness/attestation/gaps/evaluation/GUI/finalize/version cases |
| Policy/schema/approval identity | V1 | V2; exact approval prefix APPROVE_PHASE2A_POLICY_V2 and status PASS_T_PHASE2A_POLICY_V2_FROZEN_AWAITING_APPROVAL |
| Next policy correction | New V2 | A later new version; no patch to frozen V2 |

## Exact schema changes

- Root schema identity changes: `$id`, `title`, `description` and `properties/schema_version/const` → PASS_T_EVENT_GT_V2.
- Add root properties `event_list_exhaustiveness` and `event_list_exhaustiveness_attestation`. The original 36 globally required root fields are **unchanged**. Both new fields are outcome-conditional, not globally required.
- Add one `$defs/event_list_exhaustiveness_attestation` object: exactly four required boolean-true statements, additionalProperties=false.
- Append exactly three `allOf` conditions; the original nine conditions remain byte-equivalent as JSON values:
  1. Confirmed requires exhaustiveness; all other outcomes prohibit both new fields.
  2. Exhaustive confirmed requires four-part attestation/full coverage; all other cases prohibit the attestation object.
  3. Non-exhaustive/unknown confirmed requires explicit window-level completeness uncertainty.
- No change to existing event records, event types, temporal representations, states, visibility, last-confirmed semantics, markers, citation kinds/roles, references, attestations, submission metadata or round linkage.
- Cross-frame start/middle/end membership, human visual truth and derived evaluation flags are semantic requirements, not falsely claimed to be proved by JSON Schema. Explicit structured contradictions are rejectable; a checkbox alone cannot prove a visual judgment.

Exact structural difference paths:

```json
[
  {
    "path": "/$id",
    "change": "CHANGED"
  },
  {
    "path": "/title",
    "change": "CHANGED"
  },
  {
    "path": "/description",
    "change": "CHANGED"
  },
  {
    "path": "/properties/schema_version/const",
    "change": "CHANGED"
  },
  {
    "path": "/properties/event_list_exhaustiveness",
    "change": "ADDED"
  },
  {
    "path": "/properties/event_list_exhaustiveness_attestation",
    "change": "ADDED"
  },
  {
    "path": "/$defs/event_list_exhaustiveness_attestation",
    "change": "ADDED"
  },
  {
    "path": "/allOf",
    "change": "CHANGED"
  }
]
```

## Exact machine-policy changes

Seven existing metadata paths change for V2 identity/gate. Four root sections are added: `revision`, `event_list_exhaustiveness`, `event_evaluation`, `planned_v2_enforcement`. The old unconditional `outcome_rules/confirmed_not_exhaustive=true` is replaced by `outcome_rules/confirmed_exhaustiveness`, explicitly conditional on validated EXHAUSTIVE_ATTESTED. This is necessary to avoid contradicting the new exhaustive option. Every other existing rule remains equal to V1.

```json
[
  {
    "path": "/policy_id",
    "change": "CHANGED"
  },
  {
    "path": "/schema_version",
    "change": "CHANGED"
  },
  {
    "path": "/human_policy",
    "change": "CHANGED"
  },
  {
    "path": "/response_schema",
    "change": "CHANGED"
  },
  {
    "path": "/approval/message_prefix",
    "change": "CHANGED"
  },
  {
    "path": "/approval/hash_source",
    "change": "CHANGED"
  },
  {
    "path": "/status_stage_a",
    "change": "CHANGED"
  },
  {
    "path": "/revision",
    "change": "ADDED"
  },
  {
    "path": "/event_list_exhaustiveness",
    "change": "ADDED"
  },
  {
    "path": "/event_evaluation",
    "change": "ADDED"
  },
  {
    "path": "/planned_v2_enforcement",
    "change": "ADDED"
  },
  {
    "path": "/outcome_rules/confirmed_not_exhaustive",
    "change": "REMOVED"
  },
  {
    "path": "/outcome_rules/confirmed_exhaustiveness",
    "change": "ADDED"
  }
]
```

## Draft input contract and plan changes

The V2 copy of the non-binding input draft changes only the title/version association and adds the completeness/evaluation evidence boundary. Sampling, frame count, prompt/model settings, future arms, matching tolerances and hallucination-rate scoring/denominators remain reserved for Phase 2b. No model run or transmission is authorized.

The V2 plan adds GUI/validator/finalize/test requirements above, uses a separate future phase2a_v2 module namespace and v2 launcher names, and retains Stage A hard stop. Production code has not been created.

## Explicitly unchanged behavior and limitations

Preserve Phase1c selected IDs/eligibility, exclusion of test8 W06, 7 eligible windows / 7 non-overlap groups / 6 source files, dedup canonical key/item IDs, original causality and formal status, target dependence/sensitivity strata, human-seeded scope, allowed asset/reference access, native PTS/index authority, chronology, markers, immutable storage and blinded repeat. The repeat hash seed intentionally stays `PASS_T_PHASE2A_REPEAT_V1|` so this amendment does not change its prospective subset algorithm. Recommended delay remains 7 days. No negative controls, unknown independent recording sessions, single-reviewer/circularity limitations and local-receipt limitations remain.

Human completeness is a stated judgment, not externally verified truth. Even an exhaustive GT list does not guarantee a future subsampled model receives the needed evidence or resolve all matching/timing uncertainty. Full-window metrics are not computed in Stage A; formal evaluation eligibility is not granted.

