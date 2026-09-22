# V2 — Event-Driven VLM Semantic Scene Graph Memory

You are modifying an EXISTING working Python project.

Do NOT rebuild the repository from scratch.

The project already has a functioning V1 pipeline that processes:

```text
task1.mp4
task2.mp4
```

using:

```text
Video
→ Episode Segmentation
→ YOLO11s Detection
→ Tracking
→ Anchor Selection
→ RGB 2D Relative Relations
→ Temporal Filtering
→ Memory Graph
→ JSON / PNG / Annotated Video
```

V1 runs successfully and all current tests pass.

Preserve V1 code and outputs where useful.

Do NOT delete V1.

Create V2 as an upgraded pipeline that can coexist with V1 for comparison.

---

# 1. Why V2 Is Needed

Actual V1 inspection revealed several important limitations.

## Problem 1 — YOLO labels are not reliable semantic truth

Examples observed in the actual videos:

```text
basketball → detected as cup
trash can → detected as cup
miscellaneous objects → incorrect / noisy COCO labels
```

Therefore:

```text
YOLO class ≠ trusted semantic class
```

YOLO should primarily provide:

```text
bounding boxes
short-term object proposals
tracking support
temporal observations
```

It should NOT be the final semantic authority.

---

## Problem 2 — V1 graph is anchor-centric

V1 primarily produces structures like:

```text
book_03 → chair_10
cup_01  → chair_10

cup_01 → chair_11
```

This is useful as a basic anchor-relative representation, but it is NOT the desired semantic scene graph.

V2 should instead produce structures conceptually like:

```text
                         orange
                            ↑
                      basketball_01
                       /          \
                   NEAR          HELD_BY
                    ↓               ↓
                chair_03        person_01
                    │
                 LEFT_OF
                    ↓
                 table_01
```

The graph should contain:

```text
entities
attributes
semantic relationships
interactions
temporal states
```

Anchors may remain metadata, but MUST NOT determine graph topology.

---

# 2. Core V2 Design

Implement the following architecture:

```text
                           VIDEO
                             │
                             ▼
                    YOLO + TRACKING
                             │
                             ▼
                    TRACK TIMELINES
                             │
                             ▼
                    EVENT PROPOSAL
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
     appearance          interaction        disappearance
       change             candidate           candidate
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
                       EVENT WINDOWS
                    before / during / after
                             │
                             ▼
                     VLM SCENE ANALYSIS
                             │
                structured semantic JSON
                             │
                             ▼
                   GRAPH VALIDATION/FUSION
                     /                  \
                 VLM evidence       geometry/tracks
                     \                  /
                             ▼
                    EVENT SCENE GRAPH
                             │
                             ▼
                    TEMPORAL GRAPH FUSION
                             │
                             ▼
                  SEMANTIC MEMORY GRAPH
```

The key design principle is:

> Use cheap deterministic vision continuously, and use expensive semantic reasoning selectively.

Do NOT call the VLM on every frame.

---

# 3. Scope of V2

V2 MUST implement:

```text
YOLO detection
tracking
track timeline construction
event proposal
event-window keyframe selection
VLM abstraction/backend
multi-image VLM event analysis
structured scene graph output
semantic entity correction
attributes
semantic relationships
human-object interactions
geometry validation
scene graph snapshots
temporal memory graph
visualization
debug outputs
```

V2 MUST NOT implement yet:

```text
SLAM
global 3D reconstruction
monocular depth
lost-object candidate ranking
lost-object search reasoning
route planning
LLM final reasoning
FindMind UI
Streamlit
```

Those are later versions.

---

# 4. Preserve V1

Do not overwrite V1 outputs.

Use separate V2 outputs:

```text
outputs_v2/
├── task1/
└── task2/
```

or equivalent.

V1 must remain runnable.

V2 should have separate scripts such as:

```text
scripts/run_video_v2.py
scripts/run_all_v2.py
scripts/inspect_memory_v2.py
```

---

# 5. Recommended V2 Project Structure

Preserve existing modules where appropriate.

Add approximately:

```text
src/memory_graph/
│
├── video/
│   ├── reader.py
│   └── episode_segmenter.py
│
├── perception/
│   ├── detector.py
│   ├── tracker.py
│   ├── track_manager.py
│   └── track_timeline.py
│
├── events/
│   ├── __init__.py
│   ├── models.py
│   ├── interaction_signals.py
│   ├── event_proposer.py
│   └── keyframe_selector.py
│
├── vlm/
│   ├── __init__.py
│   ├── base.py
│   ├── local_backend.py
│   ├── prompts.py
│   ├── schemas.py
│   └── parser.py
│
├── scene_graph/
│   ├── __init__.py
│   ├── models.py
│   ├── builder.py
│   ├── validator.py
│   └── fusion.py
│
├── spatial/
│   ├── geometry.py
│   ├── relation_extractor.py
│   └── anchor_selector.py
│
├── memory/
│   ├── temporal_memory.py
│   ├── transition_builder.py
│   └── memory_store.py
│
├── visualization/
│   ├── event_visualizer.py
│   ├── scene_graph_visualizer.py
│   ├── memory_graph_visualizer.py
│   └── video_visualizer.py
│
└── pipeline_v2.py
```

Minor structural changes are acceptable if justified.

Do NOT put V2 into one giant script.

---

# 6. Stage A — Detection and Tracking

Continue using the existing working YOLO + tracker implementation.

YOLO is responsible for:

```text
object proposals
bounding boxes
detector confidence
initial detector class
```

Tracking is responsible for:

```text
short-term track continuity
```

Every observation must preserve:

```text
track_id
detector_class
detector_confidence
bbox
bbox_center
frame_index
timestamp
```

Important:

```text
detector_class is evidence, NOT semantic truth.
```

Do not rename the track based only on YOLO.

---

# 7. Build Track Timelines

For every track, create a temporal timeline.

Example:

```json
{
  "track_id": 17,
  "detector_class": "cup",
  "first_seen": 4.2,
  "last_seen": 13.6,
  "observations": [
    {
      "timestamp": 4.2,
      "bbox": [100, 200, 160, 270]
    }
  ]
}
```

Also derive temporal signals:

```text
visibility
bbox area
center position
velocity
direction
nearest tracks
distance to person tracks
co-motion with nearby tracks
appearance/disappearance
```

These signals will be used by event proposal.

---

# 8. Event Proposal Layer

This is one of the most important V2 modules.

Do NOT simply sample one frame every N seconds.

Detect candidate semantic events using tracking and geometric signals.

Create:

```python
EventProposal
```

with approximately:

```python
event_id
event_type
start_time
peak_time
end_time
involved_track_ids
signal_evidence
confidence
```

---

# 9. Event Type — APPEARANCE

Create an appearance event when a persistent track first becomes visible.

Avoid creating events for one-frame noise.

Require configurable persistence such as:

```text
minimum observations
minimum visible duration
minimum detector confidence
```

Example:

```json
{
  "event_type": "appearance",
  "peak_time": 5.4,
  "involved_track_ids": [17]
}
```

---

# 10. Event Type — DISAPPEARANCE_CANDIDATE

Create a disappearance candidate when a previously persistent track stops being detected.

Do NOT label this as:

```text
lost
moved
removed
```

Those conclusions are not yet justified.

Use:

```text
disappearance_candidate
```

Example:

```text
visible
visible
visible
missing
missing
missing
```

→ candidate event.

---

# 11. Event Type — PROXIMITY_CHANGE

Monitor meaningful changes in normalized image-space distance between tracks.

Especially prioritize:

```text
person ↔ portable object
portable object ↔ scene object
```

For tracks A and B derive:

```text
normalized center distance
bbox overlap
relative displacement
```

Detect patterns such as:

```text
far
far
nearer
near
very near
```

or the reverse.

Do not classify the interaction yet.

Only generate an event proposal.

---

# 12. Event Type — MOTION_COUPLING

Estimate simple track motion vectors:

```text
v_A
v_B
```

When two nearby tracks begin moving together for a persistent period, generate:

```text
motion_coupling_candidate
```

This is especially useful for:

```text
person + portable object
```

Do NOT directly conclude:

```text
HOLDING
CARRYING
```

The VLM will inspect the visual event.

---

# 13. Event Type — RELATION_CHANGE

Use the existing lightweight geometric relations as event signals.

Example:

```text
object NEAR chair
↓
object NEAR person
↓
object NEAR table
```

A persistent change in neighborhood/context should generate a relation-change event.

Again:

```text
geometry proposes event
VLM interprets event
```

---

# 14. Event Merging

Multiple signals may refer to the same real event.

Example:

```text
proximity_change
+
motion_coupling
+
disappearance_candidate
```

within the same short time interval may represent one interaction.

Merge temporally overlapping event proposals when they involve overlapping track IDs.

Produce one combined event:

```json
{
  "event_id": "evt_007",
  "event_type": "interaction_candidate",
  "start_time": 11.8,
  "peak_time": 12.6,
  "end_time": 13.5,
  "involved_track_ids": [3, 17],
  "signals": [
    "proximity_change",
    "motion_coupling",
    "disappearance_candidate"
  ]
}
```

Avoid generating many duplicate VLM calls for the same event.

---

# 15. Event Priority

Not all events are equally important.

Assign an event priority score based on evidence such as:

```text
number of supporting signals
duration
track persistence
person-object involvement
appearance/disappearance
motion change
relation change
```

Use this ONLY to decide which events deserve VLM analysis.

Do NOT reuse the old FindMind lost-object scoring formula.

This is event-selection logic, not search-candidate ranking.

---

# 16. Event Window

For each selected event, construct a temporal window.

Default concept:

```text
BEFORE
DURING
AFTER
```

For example:

```text
peak = 12.6 s

before = 11.6 s
during = 12.6 s
after  = 13.6 s
```

Make offsets configurable.

Do not assume exactly ±1 second is always optimal.

---

# 17. Keyframe Selection

For each event window, select approximately 3 representative frames:

```text
before
during
after
```

If one selected frame is blurred or missing the involved tracks, search nearby sampled frames for a better representative frame.

Prefer frames where:

```text
involved tracks are visible
bounding boxes are sufficiently large
detector confidence is high
image sharpness is acceptable
```

Save the selected frame metadata.

---

# 18. Prepare VLM Input Images

This is mandatory.

The VLM should receive images annotated with stable track identifiers.

For each selected frame:

1. start from the original RGB frame
2. draw subtle bounding boxes around relevant tracked objects
3. label them:

```text
ID:3
ID:17
ID:22
```

Optionally include the detector hypothesis in smaller text:

```text
ID:17 | detector: cup?
```

Do NOT replace the image crop with only bounding boxes.

The VLM needs scene context.

Avoid excessive overlays that obscure the objects.

Save these images:

```text
outputs_v2/task1/events/evt_007/
├── before.jpg
├── during.jpg
└── after.jpg
```

---

# 19. VLM Backend Abstraction

Do NOT tightly couple the project to one model.

Create an interface such as:

```python
class VLMBackend:
    def analyze_event(
        self,
        images,
        track_metadata,
        event_metadata,
    ) -> VLMSceneGraphResult:
        ...
```

The rest of the pipeline must not care which VLM implementation is used.

---

# 20. Hardware Detection Before Choosing Local VLM

Before installing or loading a large VLM:

1. detect whether CUDA is available
2. if CUDA exists, inspect GPU name and VRAM
3. report the result
4. choose a practical local model compatible with the hardware

Do NOT blindly download a huge model.

If no practical local VLM can run on the current hardware:

* still implement the full VLM backend abstraction
* provide a clearly documented configurable backend
* do NOT fake VLM results
* do NOT silently substitute random heuristic labels

The pipeline must fail gracefully or allow event generation to run independently.

Prefer a current practical open-source vision-language model capable of:

```text
multiple images
visual object understanding
structured prompting
JSON-like structured output
```

Choose based on actual hardware compatibility.

---

# 21. VLM Responsibilities

The VLM should analyze:

```text
before
during
after
```

together.

Its responsibilities are:

### Entity semantics

Determine the likely semantic identity of relevant track IDs.

Example:

```text
YOLO:
ID 17 = cup

VLM:
ID 17 = basketball
```

### Attributes

Infer only visually supported attributes such as:

```text
color
basic appearance
coarse state
```

### Spatial relations

Infer visible relationships.

### Human-object interactions

Infer event-level relationships such as:

```text
HOLDING
PICKING_UP
PUTTING_DOWN
CARRYING
TOUCHING
```

when visually supported.

### Temporal change

Compare before/during/after.

Example:

```text
before:
basketball on floor

during:
person touching basketball

after:
person holding basketball
```

---

# 22. The VLM Must NOT Control Identity

This is mandatory.

Track IDs come from the tracking system.

The VLM MUST NOT:

```text
invent new track IDs
rename IDs
merge IDs
split IDs
```

It may correct semantic labels associated with an existing ID.

Example:

```text
ID 17
detector_class = cup
VLM semantic_class = basketball
```

Track identity remains:

```text
17
```

---

# 23. VLM Prompt Rules

Create prompts in:

```text
src/memory_graph/vlm/prompts.py
```

The prompt must explicitly tell the VLM:

```text
You are analyzing multiple ordered frames from one short video event.

The frames are ordered BEFORE → DURING → AFTER.

Tracked objects have fixed numeric IDs drawn on the images.

Never invent a track ID.

Never change a track ID.

Only describe entities corresponding to supplied track IDs.

Correct detector labels when visual evidence strongly supports another class.

If uncertain, use "unknown".

Only infer relationships visible from the supplied frames.

Do not infer hidden actions, ownership, intention, or causality.

Return structured JSON only.
```

---

# 24. Controlled Predicate Vocabulary

For V2 use a controlled relationship vocabulary.

## Spatial

```text
LEFT_OF
RIGHT_OF
ABOVE
BELOW
NEAR
OVERLAPPING
ON
INSIDE
```

## Human-object interaction

```text
HOLDING
PICKING_UP
PUTTING_DOWN
CARRYING
TOUCHING
```

## Visibility/state

```text
VISIBLE
PARTIALLY_OCCLUDED
```

Allow:

```text
UNKNOWN
```

Do not allow arbitrary free-text predicates in the final graph.

The VLM may provide a short explanation field for debugging, but graph predicates must map to the controlled vocabulary.

---

# 25. Structured VLM Output

Do NOT accept free-form prose as the main result.

Create a Pydantic schema approximately like:

```python
class VLMEntity:
    track_id: int
    semantic_class: str
    confidence: float
    attributes: dict[str, str]

class VLMRelation:
    subject_track_id: int
    predicate: str
    object_track_id: int
    confidence: float
    temporal_phase: str

class VLMSceneGraphResult:
    event_id: str
    entities: list[VLMEntity]
    relations: list[VLMRelation]
    summary: str | None
```

`temporal_phase` should be one of:

```text
before
during
after
persistent
transition
```

Validate every VLM response.

Reject invalid IDs or predicates.

---

# 26. Example Desired VLM Output

Example:

```json
{
  "event_id": "evt_007",

  "entities": [
    {
      "track_id": 3,
      "semantic_class": "person",
      "confidence": 0.99,
      "attributes": {}
    },
    {
      "track_id": 17,
      "semantic_class": "basketball",
      "confidence": 0.91,
      "attributes": {
        "color": "orange"
      }
    }
  ],

  "relations": [
    {
      "subject_track_id": 17,
      "predicate": "NEAR",
      "object_track_id": 3,
      "confidence": 0.84,
      "temporal_phase": "before"
    },
    {
      "subject_track_id": 3,
      "predicate": "PICKING_UP",
      "object_track_id": 17,
      "confidence": 0.82,
      "temporal_phase": "during"
    },
    {
      "subject_track_id": 3,
      "predicate": "HOLDING",
      "object_track_id": 17,
      "confidence": 0.88,
      "temporal_phase": "after"
    }
  ]
}
```

---

# 27. Semantic Aggregation Across Events

The same track may appear in multiple VLM-analyzed events.

Do NOT rename it independently per event.

Aggregate semantic evidence.

Example:

```text
event 1:
ID17 → basketball 0.82

event 2:
ID17 → basketball 0.91

event 3:
ID17 → ball 0.73
```

Final semantic identity should likely be:

```text
basketball
```

Store:

```text
detector class
VLM semantic evidence
final semantic class
confidence
```

Example:

```json
{
  "track_id": 17,
  "detector_class": "cup",
  "semantic_class": "basketball",
  "semantic_confidence": 0.89
}
```

Do NOT hard-code task-specific corrections.

---

# 28. Unknown Is Valid

If semantic evidence is weak or inconsistent:

```text
semantic_class = unknown
```

is valid.

Never force:

```text
cup
chair
book
```

merely because YOLO predicted it.

A clean unknown entity is preferable to a wrong semantic entity.

---

# 29. Entity Admission / Memory Promotion

Not every YOLO track should become a persistent memory node.

Create an admission policy.

A track may be promoted based on evidence such as:

```text
temporal persistence
number of observations
participation in a meaningful event
VLM confirmation
semantic confidence
visual size
```

Keep rejected tracks available for debugging.

Save:

```text
confirmed_entities.json
rejected_tracks.json
```

Include rejection reasons.

---

# 30. Do Not Delete Real Multiple Same-Class Objects

There are genuinely multiple chairs.

Therefore:

```text
chair_01
chair_02
chair_03
chair_04
```

may all be valid.

Do NOT merge entities merely because:

```text
semantic_class == chair
```

Track identity and semantic class are different concepts.

---

# 31. Persistent Entity Naming

After semantic aggregation, create human-readable graph entity IDs.

Example:

```text
track 17
→ semantic basketball
→ basketball_01
```

Another distinct basketball:

```text
track 31
→ basketball_02
```

Preserve mapping:

```json
{
  "track_id": 17,
  "entity_id": "basketball_01"
}
```

Do NOT lose the original tracker identity.

---

# 32. Geometry Validation Layer

Do NOT throw away V1 geometric reasoning.

Use it as grounding evidence.

Architecture:

```text
VLM semantic relation
          │
          ▼
      GRAPH FUSION
          ▲
          │
tracking + bbox geometry
```

Examples:

### Agreement

```text
VLM:
basketball NEAR chair

geometry:
NEAR strongly supported
```

→ increase / preserve confidence.

### Conflict

```text
VLM:
basketball ON chair

geometry:
objects are far apart in image
```

→ lower confidence or reject.

Do NOT blindly trust either VLM or geometry.

---

# 33. Relation Source Metadata

Every final relation should record its evidence source.

Example:

```json
{
  "subject": "basketball_01",
  "predicate": "NEAR",
  "object": "chair_03",
  "confidence": 0.91,

  "evidence": {
    "vlm": true,
    "geometry": true,
    "tracking": true
  }
}
```

For semantic interactions such as:

```text
PICKING_UP
```

geometry may only provide supporting temporal evidence rather than directly confirming the predicate.

Represent this honestly.

---

# 34. Scene Graph Representation

V2 scene graphs must be general semantic scene graphs.

Entities may relate to ANY relevant entity.

Do NOT restrict relations to:

```text
dynamic object → anchor
```

Example:

```text
person_01 → HOLDING → basketball_01

basketball_01 → NEAR → chair_03

chair_03 → LEFT_OF → table_01
```

Anchor status should only be metadata:

```json
{
  "entity_id": "table_01",
  "is_anchor": true,
  "anchor_score": 0.91
}
```

---

# 35. Attributes

Attributes should be attached to entities.

For V2 prioritize visually grounded attributes:

```text
color
coarse appearance
motion state
```

Do not infer:

```text
ownership
value
importance
intention
```

unless explicitly observable, which normally they are not.

---

# 36. Event Scene Graph

For every VLM-analyzed event, create:

```text
outputs_v2/task1/events/evt_007/
├── before.jpg
├── during.jpg
├── after.jpg
├── event.json
├── vlm_raw.json
├── scene_graph.json
└── scene_graph.png
```

The scene graph PNG should visually resemble a classical semantic scene graph.

Recommended conventions:

```text
entity nodes = one visual style
attribute nodes = another visual style
relations = labeled edges or relation nodes
```

Do NOT make one panel per anchor.

---

# 37. Scene Graph Visualization

A desired visualization concept:

```text
                         orange
                            ↑
                            │
                      basketball_01
                      /            \
                  NEAR             HELD_BY
                   ↓                  ↓
               chair_03           person_01
                   │
                LEFT_OF
                   ↓
                table_01
```

Attributes should be visually distinguishable.

Anchors may have a special border or small marker but should remain ordinary entity nodes.

---

# 38. Temporal Memory Graph

After processing all selected events, fuse event graphs into a temporal memory graph.

The memory graph should preserve:

```text
persistent entities
semantic identities
attributes
stable relations
interaction events
relation transitions
timestamps
event references
```

Example:

```text
basketball_01

0–8 s:
NEAR chair_03

10.2 s:
PICKING_UP by person_01

11–16 s:
HELD_BY / carried by person_01
```

The memory graph should therefore represent:

```text
what existed
+
what relationships existed
+
what changed
+
when it changed
```

---

# 39. Do Not Flatten Time Away

Do not create only one timeless graph.

Each relation should preserve temporal information.

Example:

```json
{
  "subject": "person_01",
  "predicate": "HOLDING",
  "object": "basketball_01",
  "start_time": 10.8,
  "end_time": 15.2,
  "confidence": 0.88,
  "event_ids": ["evt_007", "evt_008"]
}
```

---

# 40. Memory Graph Output

Produce:

```text
outputs_v2/task1/memory_graph.json
outputs_v2/task1/memory_graph.png

outputs_v2/task2/memory_graph.json
outputs_v2/task2/memory_graph.png
```

The JSON should contain approximately:

```json
{
  "video": "task1.mp4",

  "entities": [],

  "attributes": [],

  "relations": [],

  "events": [],

  "transitions": []
}
```

Keep it human-readable.

---

# 41. Memory Graph Visualization

The V2 memory graph must NOT look like the V1 anchor-panel graph.

Do NOT create:

```text
Anchor chair_01
  ├── cup
  ├── book

Anchor chair_02
  └── phone
```

Instead create ONE semantic network.

Use layout techniques that keep it readable.

If the full graph is too large:

1. create a main graph containing meaningful confirmed entities and important relations
2. create detailed per-event graphs
3. optionally create paginated/detail graph views

Do not silently omit information from JSON merely to make PNG prettier.

---

# 42. Graph Sparsification

Avoid graph spaghetti.

Do NOT render every possible geometric relation.

Prioritize:

```text
VLM-confirmed semantic relations
human-object interactions
temporally stable relations
relations involved in transitions
high-confidence spatial relations
```

For purely geometric spatial relations, limit to meaningful nearest neighbors.

Do not generate all N² pairs.

---

# 43. Episode vs Event

Keep these concepts separate.

```text
Episode
= larger temporal chunk

Event
= local meaningful state-change candidate
```

Conceptually:

```text
Video
└── Episode 01
    ├── Event 001
    ├── Event 002
    └── Event 003
```

V2 event detection should work even if V1 episode segmentation returns only one episode for a short video.

Do NOT require multiple episodes.

---

# 44. Annotated V2 Video

Generate:

```text
outputs_v2/task1/annotated_v2.mp4
outputs_v2/task2/annotated_v2.mp4
```

Show:

```text
track ID
final semantic label when available
detector label when different
event markers
```

Example:

```text
ID 17
basketball
YOLO: cup
```

When an event occurs:

```text
EVENT evt_007
interaction_candidate
```

Avoid excessive clutter.

---

# 45. Event Timeline Visualization

Create:

```text
outputs_v2/task1/event_timeline.png
```

showing events over video time.

Conceptually:

```text
0s                                            30s
|-----------------------------------------------|

       APPEAR
          ▲

                PROXIMITY
                    ▲

                       INTERACTION
                           ▲

                            DISAPPEAR
                                ▲
```

Include involved entity/track IDs where readable.

This is important for debugging event proposal.

---

# 46. Debug Outputs

Save intermediate V2 outputs:

```text
outputs_v2/task1/
├── video_metadata.json
├── track_timelines.json
├── raw_event_proposals.json
├── merged_events.json
├── confirmed_entities.json
├── rejected_tracks.json
├── semantic_aggregation.json
├── event_timeline.png
├── events/
│   ├── evt_001/
│   ├── evt_002/
│   └── ...
├── memory_graph.json
├── memory_graph.png
└── annotated_v2.mp4
```

The pipeline must remain inspectable.

---

# 47. Configuration

Add V2 configuration sections.

Example:

```yaml
events:
  min_track_duration: 0.8
  min_observations: 3

  before_offset_seconds: 1.0
  after_offset_seconds: 1.0

  proximity_change_threshold: 0.15
  motion_coupling_threshold: 0.75

  merge_window_seconds: 1.5

  max_vlm_events: 20

keyframes:
  require_involved_track_visibility: true
  sharpness_weight: 0.2
  bbox_area_weight: 0.3
  detector_confidence_weight: 0.2

vlm:
  backend: "auto"
  confidence_threshold: 0.55
  allow_unknown: true

graph:
  max_geometric_neighbors: 3
  min_relation_confidence: 0.55
```

These numbers are initial defaults, not scientific truths.

Document them.

---

# 48. Limit Number of VLM Calls

This is important.

V2 is specifically designed to avoid analyzing every frame.

Implement:

```text
max_vlm_events
```

If more events exist than the configured limit:

```text
rank by event priority
```

and analyze only the highest-priority events.

Still save all raw event proposals.

Report:

```text
total proposed events
merged events
VLM-analyzed events
skipped events
```

---

# 49. Caching

VLM inference may be expensive.

Cache results.

If:

```text
evt_007
```

has already been analyzed with the same:

```text
frames
model
prompt version
```

do not rerun it unnecessarily.

Store enough metadata to invalidate cache when inputs change.

---

# 50. Tests

Preserve all V1 tests.

Add V2 tests that do NOT require a real VLM.

Use a mock VLM backend.

At minimum test:

## Event proposal

Synthetic tracks approaching each other should generate proximity-change event.

## Disappearance

Persistent track followed by sustained absence should generate:

```text
disappearance_candidate
```

## Motion coupling

Two nearby tracks moving similarly should generate candidate interaction signal.

## Event merging

Overlapping:

```text
proximity
motion coupling
disappearance
```

should merge appropriately.

## Keyframe selection

Before/during/after timestamps should be correct and valid.

## VLM parser

Invalid track IDs must be rejected.

## Predicate validation

Unsupported predicates must not enter the graph.

## Semantic correction

Mock:

```text
YOLO = cup
VLM = basketball
```

should produce:

```text
semantic_class = basketball
detector_class = cup
```

while preserving track identity.

## Unknown

Weak mock evidence should produce:

```text
unknown
```

rather than forced label.

## Multiple chairs

Several separate chair tracks must remain separate entities.

## Graph fusion

VLM + geometry agreement should retain relation.

Strong geometry conflict should lower/reject spatial relation according to configured rules.

## Temporal memory

Repeated event relations should merge into intervals without losing timestamps.

---

# 51. VLM Failure Must Not Crash Entire Pipeline

If one event fails VLM parsing or inference:

```text
log error
save failure metadata
continue with remaining events
```

Do not lose the entire video run.

Memory graph should indicate which events lacked semantic analysis.

---

# 52. Scientific Honesty

Do NOT claim:

```text
true 3D relation
world coordinate relation
physical support
object permanence
causal action
```

unless actually supported.

V2 remains:

```text
RGB
+
tracking
+
image geometry
+
VLM semantic interpretation
```

Spatial relations remain primarily image-relative.

Human-object interaction predicates are VLM interpretations grounded by temporal frames and tracking evidence.

Document this clearly.

---

# 53. Actual Execution Requirements

Do not merely write code.

After implementation:

1. inspect existing V1 code
2. preserve working V1
3. implement V2 modules
4. run all unit tests
5. run V2 event proposal on task1
6. inspect proposed events
7. run available VLM backend if hardware supports it
8. inspect actual event scene graphs
9. run task2
10. inspect results
11. fix obvious runtime errors
12. verify all required files exist

Do NOT fabricate VLM results if local inference is unavailable.

---

# 54. Mandatory Manual Checks on task1

Specifically inspect:

```text
basketball previously detected as cup
trash can previously detected as cup
multiple real chairs
miscellaneous noisy detections
```

Report:

### Basketball

Did VLM correct it?

If yes:

```text
YOLO: cup
VLM: basketball
```

If not, report actual result.

### Trash can

Same check.

### Chairs

Confirm that genuinely separate chairs remain separate track/entity IDs.

### Noise

Report how many tracks were rejected from semantic memory and why.

Do not hard-code corrections for these known objects.

---

# 55. V1 vs V2 Comparison

Generate a concise comparison report.

For each video:

```text
V1 raw track IDs
V2 raw track IDs

V2 proposed events
V2 merged events
V2 VLM-analyzed events

V2 confirmed semantic entities
V2 unknown entities
V2 rejected tracks

YOLO → VLM semantic corrections

V2 semantic relations
V2 interaction relations
V2 temporal transitions
```

Do not claim V2 is better merely because it has fewer nodes.

Assess semantic cleanliness and usefulness.

---

# 56. README V2

Update documentation with:

```text
V1 architecture
V2 architecture
why V2 exists
event proposal logic
VLM responsibilities
VLM limitations
scene graph schema
memory graph schema
how to run V2
how to inspect outputs
```

Add Mermaid:

```text
Video
  ↓
YOLO + Tracking
  ↓
Track Timeline
  ↓
Event Proposal
  ↓
Before / During / After
  ↓
VLM
  ↓
Structured Scene Graph
  ↓
Geometry Validation
  ↓
Temporal Memory Graph
```

---

# 57. CLI

Support:

```bash
uv run python scripts/run_video_v2.py task1.mp4
```

and:

```bash
uv run python scripts/run_all_v2.py
```

Allow event-only mode:

```bash
uv run python scripts/run_video_v2.py task1.mp4 --events-only
```

This should:

```text
run detection/tracking
generate event proposals
select keyframes
save event images
```

without requiring VLM inference.

Also support:

```bash
uv run python scripts/inspect_memory_v2.py outputs_v2/task1/memory_graph.json
```

---

# 58. Useful Console Output

Example:

```text
[INFO] Processing task1.mp4
[INFO] Building track timelines...
[INFO] 77 raw track IDs

[INFO] Detecting event candidates...
[INFO] 34 raw signals
[INFO] 12 merged events

[INFO] Selecting event keyframes...
[INFO] 12 event windows prepared

[INFO] VLM backend: ...
[INFO] Analyzing event 1/12
[INFO] Semantic correction: track 17 cup → basketball
[INFO] Event relation: person_03 PICKING_UP basketball_01

[INFO] Building event scene graphs...
[INFO] Building temporal memory...

[INFO] Confirmed entities: ...
[INFO] Rejected tracks: ...
[INFO] Semantic relations: ...
[INFO] Interaction relations: ...

[INFO] Saved memory_graph.json
[INFO] Saved memory_graph.png
```

Do not spam logs per frame.

---

# 59. Final Response

When complete, report:

## Environment

```text
Python
PyTorch
CUDA
GPU
VRAM if available
VLM model/backend
```

## Tests

```text
X/X passed
```

## task1

```text
raw track IDs
raw event signals
merged events
VLM-analyzed events
confirmed semantic entities
unknown entities
rejected tracks
semantic corrections
semantic relations
interaction relations
transitions
```

## task2

Same.

## Known-object checks

Explicitly report actual observed results for:

```text
basketball
trash can
multiple chairs
```

## Outputs

Point me to:

```text
event_timeline.png
events/
memory_graph.json
memory_graph.png
annotated_v2.mp4
```

## Remaining problems

Explain actual failures based on results.

## V3 recommendation

Do NOT implement V3.

Based on the real V2 output, tell me which bottleneck should be addressed next:

```text
persistent identity / ReID
camera motion
relative depth / 3D
occlusion reasoning
event proposal quality
VLM semantic quality
```

---

# 60. Definition of Done

V2 is successful when:

1. V1 remains intact.
2. Both videos can still be processed.
3. YOLO/tracking produce temporal object tracks.
4. The system proposes meaningful temporal events rather than sending every frame to VLM.
5. Each analyzed event has before/during/after images.
6. Track IDs are visibly grounded in VLM input.
7. VLM output is structured and validated.
8. VLM can correct YOLO semantic labels without changing track IDs.
9. `unknown` is allowed.
10. Real multiple chairs remain separate entities.
11. Noisy tracks are filtered before persistent memory admission.
12. Event scene graphs contain general entity/entity relationships.
13. Human-object interactions can be represented.
14. The final graph is NOT organized around anchor panels.
15. Temporal information is preserved.
16. VLM output is checked against geometry/tracking evidence.
17. Event graphs and final memory graph are visually inspectable.
18. The system does not claim to be true 3D spatial memory yet.
19. No lost-object candidate ranking or UI is implemented.
20. Actual task1/task2 results are inspected before declaring success.

The key V2 research concept is:

> Continuous low-cost perception proposes when something meaningful may have happened; selective multi-frame VLM analysis determines what happened; grounded semantic scene graphs are then consolidated into temporal memory.

Do not proceed beyond this scope.
