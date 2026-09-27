# SAM 3.1 Technical Review — V2.6.1

Reviewed 2026-09-26 before writing SAM 3.1 integration code. Technical authority: [Meta SAM 3 README](https://github.com/facebookresearch/sam3), [SAM 3.1 release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md), [official SAM 3.1 video notebook](https://github.com/facebookresearch/sam3/blob/main/examples/sam3.1_video_predictor_example.ipynb), [official checkpoint page](https://huggingface.co/facebook/sam3.1), and the cloned Meta code at revision `2345a4ad109ac29c569da749c91d84f10dc08c40` (`.sam31_official`). Local API observations below refer to that exact revision.

## OFFICIAL_DOCUMENTATION

| # | Area | Verified finding |
|---|---|---|
| 1 | Checkpoint | Official `facebook/sam3.1` file `sam3.1_multiplex.pt`, model repository revision `daa63191845a41281374e725f4c9e51c7a824460`; 3,502,755,717 bytes per authenticated HEAD. No Transformers integration is provided by the model repository. |
| 2 | Checkpoint requirements | Latest official `facebookresearch/sam3` code is required for the SAM 3.1 checkpoint; `build_sam3_multiplex_video_predictor(checkpoint_path=...)` loads it. |
| 3 | Gated access | The Hugging Face model requires login and agreement to share contact information. An authenticated HEAD for this exact file succeeded on this computer; token value is never stored in this report. |
| 4 | Repository | `https://github.com/facebookresearch/sam3`. |
| 5 | Code revision | `2345a4ad109ac29c569da749c91d84f10dc08c40`, shallow-cloned for this experiment. |
| 6 | Python | README prerequisite: Python 3.12 or newer. The package metadata says `>=3.8`, but this experiment follows the stricter README runtime requirement. |
| 7 | PyTorch | README prerequisite: PyTorch 2.7 or newer; recommended example installs 2.10.0. |
| 8 | CUDA | README prerequisite: CUDA GPU with CUDA 12.6 or newer; example uses CUDA 12.8 PyTorch wheels. |
| 9 | Installation | Create a separate Python environment; install CUDA PyTorch, clone official repository, `pip install -e .`. Notebook extras are optional. Optional FlashAttention 3/cc_torch accelerators are separate. |
| 10 | Video predictor API | The SAM 3.1 notebook uses `build_sam3_multiplex_video_predictor()`, `handle_request` and `handle_stream_request`. `build_sam3_predictor(version="sam3.1")` also routes to multiplex in the checked source. |
| 11 | Prompt types | Official README lists text, point, box, mask as SAM 3 family capabilities. For the checked SAM 3.1 video predictor, `add_prompt` directly accepts text, points, and boxes. `add_mask` raises `NotImplementedError` for the multiplex model. |
| 12 | Box | `handle_request({"type":"add_prompt", ..., "bounding_boxes":[[x,y,w,h]], "bounding_box_labels":[1]})`; source requires normalized 0–1 `xywh`. Box is treated as visual/semantic grounding and resets the prior state, unlike explicit instance points. |
| 13 | Point | `points`, `point_labels`, and explicit integer `obj_id`; point coordinates can be normalized (`rel_coordinates=True`) or absolute (`False`). Positive=1, negative=0 in the official notebook. |
| 14 | Mask | The checked multiplex implementation does **not** support caller `add_mask`; the base predictor explicitly says to use point or box. Do not assume generic SAM 3 README mask wording means a SAM 3.1 video mask prompt works. |
| 15 | Text/concept | `add_prompt` with `text` can discover and track all matching concept instances; it is a different task from target-conditioned propagation. Changing text prompts requires `reset_session`, per notebook. |
| 16 | Video initialization | `start_session` accepts an MP4 or numbered JPEG folder as `resource_path`; the notebook says initialization loads video frames into session state. |
| 17 | Propagation | Stream `{"type":"propagate_in_video", "session_id":...}`; checked code also accepts direction, starting frame, maximum frame count, probability threshold, and forced tracker propagation. |
| 18 | Object IDs | Output `out_obj_ids` are SAM internal integers; point prompts may specify `obj_id`. Semantic/box prompting may create model IDs. These are not FindMind physical IDs. |
| 19 | Memory/session | Predictor keeps a stateful session per video, with tracker memory and expiration management. `close_session` frees its resources. |
| 20 | Reset/reinitialization | `reset_session` clears to initial state; `remove_object` removes one ID. Checked box/semantic add_prompt calls `reset_state` internally. A confirmed Re-ID event may start a fresh matched-prompt window. |
| 21 | Returned masks | `outputs["out_binary_masks"]` gives per-object boolean masks; `out_boxes_xywh` gives normalized mask boxes, and `out_obj_ids` aligns the arrays. Empty masks can be omitted by postprocessing. |
| 22 | Confidence | Checked source emits `out_probs`, aligned with output IDs/masks. It is a SAM output probability, not YOLO confidence nor physical-identity confidence. |
| 23 | Object Multiplex | Fixed-capacity object buckets share tracking work/memory across objects. Release notes report ~7× throughput at 128 objects on one H100 **versus the November 2025 SAM 3 release**, not versus SAM 2.1. |
| 24 | Single-object workflow | Start one session, prompt the known target using a box or explicit-ID point, propagate, inspect its output ID and mask, close session. |
| 25 | Multi-object workflow | Prompt/discover multiple objects in one session, preserve distinct SAM IDs, propagate jointly; the official notebook demonstrates text discovery, object removal, and point addition/refinement. |
| 26 | Limitations | The official notebook demonstrates text and point prompts but no box-only worked example; mask prompting is unsupported in this multiplex video API. Model is gated, CUDA dependent, and 3.5 GB; no official claim establishes FindMind phone tracking superiority or RTX 5070 Ti runtime. |
| 27 | Difference from SAM 2.1 | SAM 3 family adds semantic concept discovery and detector/tracker design; SAM 3.1 adds Object Multiplex. Existing FindMind SAM 2.1 uses a box to condition an explicit target object and propagates it every sixth source frame. Box prompt *syntax* exists in SAM 3.1, but its semantic grounding path differs from SAM 2.1 instance box initialization. |
| 28 | FindMind relevance | A matched known-target video test is required before model choice. Object Multiplex may matter for a later many-entity Spatial Memory Graph but its 128-object benchmark does not predict a one-phone benefit. |

### Exact official benchmark context

The [release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md) report higher SAM 3.1 VOS scores on six of seven listed datasets relative to SAM 3 (for example MOSEv2 60.3 → 62.3), while video concept segmentation results are mixed (for example YT-Temporal cgF1 50.8 → 52.9 and LVVIS mAP 36.3 → 34.3). These are **SAM 3 vs SAM 3.1** numbers and are never used as SAM 2.1 vs SAM 3.1 measurements.

## PROJECT_DESIGN_INTERPRETATION

- Primary arm: use the identical frozen YOLO target box and initialization frame. Convert source-pixel `xyxy` to normalized `xywh` for the official SAM 3.1 box prompt. Record the semantic-grounding difference and check whether the returned instance overlaps the seed box before mapping it to `phone_01` in the *experimental observation* only.
- Secondary controlled fallback if box grounding cannot produce a single matched instance: a deterministic center positive point from the same frozen box, with a project-local SAM integer ID. This fallback must be labelled separately, never silently mixed into box results.
- No concept text such as `smartphone` belongs in the primary arm. Any concept trial is exploratory and separate.
- V2.6's `PROVISIONAL_MATCH` and `CONFIRMED_MATCH` authorization is the only source of reinitialization permission. A SAM mask or category prediction cannot authorize a physical identity match.
- Guard and physical-target review follow a blind prediction freeze. A nonempty wrong-object mask is drift, not continuity success.

## LOCAL_COMPATIBILITY_FINDINGS_AFTER_REVIEW

These are measured findings for this Windows RTX 5070 Ti environment, not official SAM 3.1 benchmark claims:

1. At code revision `2345a4a`, `Sam3BasePredictor.start_session` passes a default `offload_state_to_cpu=False`, but `Sam3MultiplexTrackingWithInteractivity.init_state` has no such parameter. `src/memory_graph/v261/compat.py` discards **only** that unsupported false argument; the official repository files stay unchanged.
2. The non-FA3 decoder requests only PyTorch `FLASH_ATTENTION`. This Windows PyTorch wheel reports no such kernel. The project-local compatibility layer allows `MATH` SDPA, which is a correct PyTorch backend but dramatically slower and memory intensive here.
3. The README's optional `flash-attn-3==3.0.0` CUDA 12.8 wheel imports, but inference fails on this RTX 5070 Ti with `no kernel image is available for execution on the device`. This is a local device/backend result; it does not establish general FA3 incompatibility.
4. Reducing `multiplex_count` from the checkpoint's 16 to 1 fails checkpoint loading with tensor-size mismatches. `max_num_objects=1` with `multiplex_count=16` loads, yet long-window propagation still exceeds physical VRAM capacity under the math backend.
5. The official builder emits a long first-pass missing-key message and then a second 64-key positional-buffer missing-key message; both are preserved in `outputs_v261/smoke/official_build_*.txt`. The smoke tests verify execution, not exact numerical equivalence to another installation.
