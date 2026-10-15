# Phase 2b Model Configuration Decision Sheet

No choice in this sheet has been made by the implementation run.

Required before protocol freeze:

- Exact provider, backend, model ID, revision, and local/external execution location.
- Verified support status and evidence for authorized video, multi-image, and storyboard input.
- Native-video constraints, maximum image count, maximum pixels per image, and context limit.
- Temperature, sampling mode, seed support/value, and maximum output tokens.
- Timeout, retry limit, monetary budget, and explicit external-data consent where applicable.
- Target reference policy: `NONE`, `AUTHORIZED_STATIC_REFERENCE`, or `APPROVED_NEUTRAL_LOCALIZATION`.
- Uniform frame count shared by multi-image and storyboard.
- Re-encoded video FPS and temporal-distortion acceptance.
- Event-time tolerance and bounded-interval overlap rule.
- Repeat count: one, or three only when budget permits; every repeat is retained.
- Exact run order and selected six-window pilot inventory. test3 is prohibited.

Use `model_config.template.json` and `protocol_decisions.template.json` to record the decisions. A manual `DECLARED` capability is insufficient for protocol freeze.

