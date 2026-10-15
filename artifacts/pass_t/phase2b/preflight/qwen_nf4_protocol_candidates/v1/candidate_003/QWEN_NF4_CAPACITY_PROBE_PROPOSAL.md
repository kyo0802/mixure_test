# Capacity probe proposal — do not execute

Recommended before freeze because no matched long-window resource receipt exists. Generate NEW neutral geometric synthetic media with the approved technical shapes; never reuse Phase2a pixels. Test selected multi-image, matching storyboard and full-rate video once each, one model process, no automatic fallback. Reference count and final measured pixel limits depend on protocol choices.

{
  "status": "DESIGN_ONLY_NOT_AUTHORIZED",
  "neutral_content_only": true,
  "phase2a_media": false,
  "shapes": {
    "multi_image": {
      "frames": 8,
      "dimensions": [
        1280,
        720
      ]
    },
    "storyboard": {
      "dimensions": [
        1440,
        906
      ]
    },
    "video": {
      "frames": 118,
      "dimensions": [
        1280,
        720
      ],
      "duration_s": "match chosen authorized native span",
      "codec": "FFV1/AVI",
      "processor_fps": 4
    }
  },
  "reference_count": "0 or 1 only after reference choice; neutral synthetic image",
  "image_max_pixels_proposal": 200704,
  "generation": {
    "do_sample": false,
    "max_new_tokens": 1024,
    "generation_deadline_s": 300,
    "transport_deadline_s": 330,
    "load_deadline_s": 120
  },
  "resource_stop": {
    "minimum_free_gpu_gib_before_load": 10,
    "minimum_free_ram_gib": 8,
    "global_gpu_used_stop_gib": 14.5,
    "peak_cpu_rss_stop_gib": 20,
    "one_model_only": true
  },
  "repeat": 1,
  "retry": 0,
  "max_three_generation_attempts": true,
  "required_measurements": [
    "EOS token captured explicitly",
    "generated token ids/count",
    "separate processor/prefill/generation/load/request seconds",
    "process GPU allocated/reserved peaks",
    "global GPU time series",
    "CPU RSS peak",
    "offload map",
    "selected frames/native mapping/grid/padding",
    "OOM/timeout/raw JSON/schema/citations"
  ],
  "approval_required": "separate capacity-probe authorization; neither protocol approval nor pilot command inferred",
  "implemented_execution_command": null
}

Safety: stop on cap, OOM, timeout, non-offline asset access or unexpected fallback; preserve all attempts, no frame/resolution/precision changes. Technical pass is not event reasoning correctness. Proposed exact execution command is NOT IMPLEMENTED; existing run_pass_t_qwen_nf4.py would rerun old smoke and is expressly inappropriate. Future authorized task must implement a new synthetic-only, fixed-hash probe entry point and demonstrate guards before issuing its command. No invented executable CLI is presented. The implemented/tested current offline command is `python artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/preflight.py build` (already executed; existing output prevents overwrite).
