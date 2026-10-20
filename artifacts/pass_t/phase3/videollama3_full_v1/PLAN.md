# Direct VideoLLaMA3 integration plan

- Download and pin official DAMO-NLP-SG/VideoLLaMA3-7B; inspect custom implementation. Use one isolated Transformers dependency path with existing CUDA Torch, without changing Qwen packages. Resolve actual compatibility problems in this integration, not a separate smoke project.
- Enumerate canonical frozen test1-test9 event-window records, exact available PNG frames, duplicates/overlap, source hashes and original sampling. Preserve unavailable and excluded records explicitly. Separate evaluation labels from model-visible inputs.
- Implement one real ObservationAdapter plus resumable sequential ledger. Freeze a single object-neutral observation-first task/schema before first generation. Prefer existing Uniform8 selections; no outcome-based tuning, crop selection or fresh sampling policy.
- Run actual eligible windows. Save raw text before parsing, classify outer-fence extraction separately, preserve individual failures and continue only when safe. Resume only unfinished calls, never overwrite completed predictions.
- Evaluate available reviewed GT descriptively; distinguish unreviewed outcomes. Compare Qwen only on genuinely shared frames/task conditions and disclose differences. Publish one main report through WORKSPACE/Pass_T; no Graph writes, commit or push.
