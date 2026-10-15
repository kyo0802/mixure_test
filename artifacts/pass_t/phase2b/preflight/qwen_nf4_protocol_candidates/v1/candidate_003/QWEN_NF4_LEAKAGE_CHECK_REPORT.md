# Leakage audit

| Check | Classification | Scope / limitation |
|---|---|---|
| Serialized JSON allowlist | PASS | 66 candidate payloads use existing strict payload schema; only opaque request/target/media IDs, aliases, times, task ontology/prompt |
| Human answers, event times/counts, rationale, reviewer, eligibility, scores, prior predictions | PASS | Never supplied to selection/visible builders; private eligibility is only cohort planning |
| Private paths and response provenance | PASS | Mappings physically under private; media paths are orchestration only, never user message text; directory IDs opaque |
| Source frame authority / no future frames | PASS | Hash/PTS/pixel verification and half-open membership; references absent from visible media |
| PNG metadata | PASS | RGB re-encode, empty info/exif tested |
| Storyboard artificial text | PASS | Only neutral F aliases + native PTS; no bbox or answer-derived marker |
| Video container metadata | UNABLE_TO_DETERMINE | FFV1/OpenCV no audio; all decoded pixels verified; software/container tags are not a GT label scan |
| Pixel semantic blinding | UNABLE_TO_DETERMINE | Visual spot inspection of six uniform8 sheets cannot certify absence of every contextual answer cue in all frames |
| Prompt formatting parity across deployed runtime | FAIL | Existing video runtime omits V2 system; future adapter repair needed, no runtime code modified |
| Reference model authorization | UNABLE_TO_DETERMINE | Human authorization exists for five; no protocol approval for model use |
| Runtime inference | NOT_RUN | No VLM model loaded or generated |

Ontology PICKUP/PLACEMENT definitions are task instructions and are not treated as GT leakage. The permitted original visual sequence naturally contains event evidence; that is not an answer overlay. Exact prospective message text is saved in image *_chat.txt; video serialization differences are explicitly documented. A string scan alone does not establish visual blinding. No complete leakage PASS is claimed while semantic/container/reference issues remain. Inspection notes are in visual_inspection.md.
