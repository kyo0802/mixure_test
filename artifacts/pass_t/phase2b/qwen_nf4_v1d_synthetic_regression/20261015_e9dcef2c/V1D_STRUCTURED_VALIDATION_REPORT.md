# V1D structured validation / coverage

**REGRESSION_FAIL**.

| Attempt | Representation | JSON | Schema | Semantic diagnostic | Citation diagnostic | Strict | Emitted events |
|---|---|---|---|---|---|---|---|
| R01_C01 | MULTI_IMAGE | True | False | True | True | False | 0 |
| R02_C06 | STORYBOARD | True | False | True | True | False | 2 |
| R03_C08 | NATIVE_VIDEO_ARRAY | True | False | True | True | False | 1 |
| R04_C03 | MULTI_IMAGE | True | False | True | True | False | 1 |
| R05_C04 | STORYBOARD | True | False | True | True | False | 2 |
| R06_C07 | NATIVE_VIDEO_ARRAY | True | True | True | True | True | 0 |
| R07_C02 | MULTI_IMAGE | True | False | True | True | False | 1 |
| R08_C05 | STORYBOARD | True | False | True | True | False | 2 |

Mandatory field violations (individual entries)={'event_timing_entries': 9, 'global_uncertainty': 6, 'window_citations': 1}; affected attempts={'event_timing_entries': 6, 'global_uncertainty': 6, 'window_citations': 1}; distinct category attempts={'EMPTY_WINDOW_CITATIONS': 1, 'EMPTY_TIMING_UNCERTAINTY': 6, 'SCHEMA_MINLENGTH': 6}. Target fields not evaluable due to parse failure=0; not counted as field PASS. Actual event-bearing=6/8, coverage threshold3; not physical-event recall.

## R01_C01

Raw: [runs\R01_C01\raw_output.txt](runs\R01_C01\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ['/window_cited_frame_aliases:[] should be non-empty'], 'valid': False}.

Event timing strings: `[]`.

Root `/uncertainty`: `"Insufficient evidence to confirm or deny any transition."`.

Window citations: []; nonempty=False; membership=True.

## R02_C06

Raw: [runs\R02_C06\raw_output.txt](runs\R02_C06\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ["/events/0/timing_uncertainty:'' should be non-empty", "/events/1/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"], 'valid': False}.

Event timing strings: `["", ""]`.

Root `/uncertainty`: `""`.

Window citations: ['F0001', 'F0002', 'F0003', 'F0004', 'F0005', 'F0006', 'F0007', 'F0008']; nonempty=True; membership=True.

## R03_C08

Raw: [runs\R03_C08\raw_output.txt](runs\R03_C08\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"], 'valid': False}.

Event timing strings: `[""]`.

Root `/uncertainty`: `""`.

Window citations: ['F0007']; nonempty=True; membership=True.

## R04_C03

Raw: [runs\R04_C03\raw_output.txt](runs\R04_C03\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"], 'valid': False}.

Event timing strings: `[""]`.

Root `/uncertainty`: `""`.

Window citations: ['F0002']; nonempty=True; membership=True.

## R05_C04

Raw: [runs\R05_C04\raw_output.txt](runs\R05_C04\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ["/events/0/timing_uncertainty:'' should be non-empty", "/events/1/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"], 'valid': False}.

Event timing strings: `["", ""]`.

Root `/uncertainty`: `""`.

Window citations: ['F0001', 'F0002', 'F0003', 'F0004', 'F0005', 'F0006', 'F0007', 'F0008']; nonempty=True; membership=True.

## R06_C07

Raw: [runs\R06_C07\raw_output.txt](runs\R06_C07\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': [], 'valid': True}.

Event timing strings: `[]`.

Root `/uncertainty`: `"Sparse sampling and lack of direct observation of any transition."`.

Window citations: ['F0001', 'F0002', 'F0003', 'F0004', 'F0005', 'F0006', 'F0007', 'F0008']; nonempty=True; membership=True.

## R07_C02

Raw: [runs\R07_C02\raw_output.txt](runs\R07_C02\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"], 'valid': False}.

Event timing strings: `[""]`.

Root `/uncertainty`: `""`.

Window citations: ['F0002']; nonempty=True; membership=True.

## R08_C05

Raw: [runs\R08_C05\raw_output.txt](runs\R08_C05\raw_output.txt). Strict={'citation_errors': [], 'semantic_errors': [], 'structural_errors': ["/events/0/timing_uncertainty:'' should be non-empty", "/events/1/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"], 'valid': False}.

Event timing strings: `["", ""]`.

Root `/uncertainty`: `""`.

Window citations: ['F0001', 'F0002', 'F0003', 'F0004', 'F0005', 'F0006', 'F0007', 'F0008']; nonempty=True; membership=True.

## Warnings and interpretation

All-event identical normalized timing explanation warning=True; distinct normalized event timing texts=1. Long overlap uses preregistered >=12 contiguous word tokens. Full per-attempt strings, overlap excerpts, intended/emitted disagreements and masked known-state findings in V1D_WARNING_REVIEW.json. Whitespace-only text screened separately from unchanged schema minLength.

Temporal precision, target continuity and evidential citation meaning require visual judgment and remain explicitly UNREVIEWED, not falsely declared absent or automatically scored from renderer intent. Stable/changed object renderings are not event GT. Semantic/citation shadow diagnostics do not override strict early-return. No invalid outputs repaired or replaced; no further calls/prompt tuning.
