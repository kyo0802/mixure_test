"""Narrow runtime shims for two SAM 3.1 public-code/Windows incompatibilities.

The official model and checkpoint are unchanged. The first shim removes an
unsupported default-False session argument. The second allows PyTorch's math
SDPA backend where the official decoder insists on unavailable Flash SDPA.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from pathlib import Path

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel


def enable_math_sdpa_fallback() -> None:
    import sam3.model.decoder as decoder

    # Only decoder.functional_attention uses the restrictive FLASH-only context.
    # Do not replace PyTorch operators or model weights.
    decoder.sdpa_kernel = lambda _requested: sdpa_kernel([SDPBackend.MATH])


def build_compatible_predictor(
    checkpoint: Path, build_log: Path, *, use_fa3: bool = True,
    max_num_objects: int = 16, multiplex_count: int = 16,
):
    from sam3.model_builder import build_sam3_multiplex_video_predictor

    if not use_fa3:
        enable_math_sdpa_fallback()
    with build_log.open("w", encoding="utf-8") as stream, redirect_stdout(stream):
        predictor = build_sam3_multiplex_video_predictor(
            checkpoint_path=str(checkpoint), use_fa3=use_fa3, compile=False,
            warm_up=False, async_loading_frames=False,
            max_num_objects=max_num_objects, multiplex_count=multiplex_count,
        )
    original_init = predictor.model.init_state

    def compatible_init_state(*args, offload_state_to_cpu=False, **kwargs):
        if offload_state_to_cpu:
            raise ValueError("Official SAM 3.1 multiplex init_state has no state-offload support")
        return original_init(*args, **kwargs)

    predictor.model.init_state = compatible_init_state
    return predictor
