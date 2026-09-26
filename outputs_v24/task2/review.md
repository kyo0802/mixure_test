# Task2 held-out Re-ID review

The inference audit and parameter hash were frozen before GT was read.

| Candidate | Cosine max | Inference decision | Reviewed identity |
|---|---:|---|---|
| candidate_phone_01 | 0.695 | MATCH | original smartphone |
| candidate_phone_02 | 0.460 | AMBIGUOUS | distinct desk phone |
| candidate_phone_03 | 0.498 | AMBIGUOUS | distinct desk phone |

Best-vs-second margin: 0.197; required 0.100.
Desk-phone pair cosine 0.829 with 18 reliable coexistence frames; they remain distinct.
False match count: 0. Appearance-memory poisoning: False. Same-identity SAM reinitialization authorized: True; executed: False.

This single reviewed sequence does not establish general long-gap Re-ID accuracy.
