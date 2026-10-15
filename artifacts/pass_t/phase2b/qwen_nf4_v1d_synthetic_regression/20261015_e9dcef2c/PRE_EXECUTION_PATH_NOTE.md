# Pre-execution Windows path normalization

First preregistration invocation stopped before writing criteria/manifest or loading a model because the baseline included both Windows backslash and POSIX spellings for the intentionally repaired bridge. The single allowed file comparison used POSIX only, producing a false protected-change rejection for the same file. Normalized the comparison, retaining every other hash check. No fixture/prompt/model/contract change. Original source digest and exact bounded bridge diff remain preserved. No GPU attempt occurred.
