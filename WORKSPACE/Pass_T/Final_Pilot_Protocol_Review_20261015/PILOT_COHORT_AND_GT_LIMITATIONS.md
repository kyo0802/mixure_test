# Six-window Cohort and GT Limitations

Review 67b59d603e36；proposal only。Authority：E01/E02/E03；既有 GT dataset digest 記錄為 `ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c`。本次讀 eligibility/報告/來源 metadata，未重讀或變更原 GT 內容。

| 視窗（去重單位） | Item ID / opaque ID | 用途 | 既有來源 frames / PTS span |
| --- | --- | --- | --- |
| test1__W03 / test1__W05 | PT2A_9d15d2a6b56b56d0 / W_5597d9b003977e053d70 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS | S000157–S000263 (107 frames); 5.235000–8.770000s |
| test2__W01 | PT2A_b35d807b28b92101 / W_ec4751640324779435e6 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS | S000180–S000287 (108 frames); 6.008333–9.580000s |
| test5__W01 | PT2A_fe0910d66f4c5614 / W_aef405003cc72cef0044 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS | S000162–S000233 (72 frames); 5.400000–7.766667s |
| test5__W05 | PT2A_eb60192e6986cb4f / W_f1d4f821d33515975293 | KNOWN_EVENT_MATCHING_ONLY | S000342–S000449 (108 frames); 11.400000–14.966667s |
| test7__W05 | PT2A_c58b4df88a2f6801 / W_b8a53fea6aa8b92dc94f | KNOWN_EVENT_MATCHING_ONLY | S000373–S000479 (107 frames); 12.435000–15.973333s |
| test8__W07 | PT2A_5dbb180e8ff88762 / W_db55b29f820c2b3e3afb | DESCRIPTIVE_UNCERTAINTY_ONLY | S000936–S001053 (118 frames); 31.211667–35.101667s |


## Eligibility boundaries

1. **三 strict negatives**：test1 W03/W05 去重、test2 W01、test5 W01。原 full-window negative attestation/行政 reviewer resolution 被保留；test1 新增視覺 spot check 只有7/107 frames，test2/test5 W01 無新增獨立全窗視覺複核。只報個案 event alerts，不報FPR/hallucination rate，且 valid claim 仍需人工判讀。
2. **兩 known PICKUP**：test5 W05、test7 W05，NOT_ATTESTED/non-exhaustive；僅已支持 PICKUP 可探索性一對一 matching。後段遮擋不能證明持續拿著或排除後續事件。未列出的預測為 UNEVALUATED，不自動算 FP。不能合併其他 candidate 身分或解除既有target-association/causality限制。
3. **一 uncertain**：test8 W07，INSUFFICIENT_EVIDENCE，只 descriptive/abstention 分析；不轉成 NO_EVENT、不當完整負例。
4. **Excluded**：test3 W07 (`PT2A_0bfb99c324769681`) 保留污染/暴露排除，沒有模型call；負責人對誤勾的澄清不是解隔離。
5. 沒有 validated PLACEMENT positive，也沒有 exhaustive positive。全部 formal_benchmark_permission=false；causality/status與session獨立性未證實。不能報 accuracy、precision、recall、F1、false-positive rate、hallucination rate、generalization或統計優越性。

## Source/time metadata verification scope

六窗皆在既有 `private/source.json` ordered list 上重現 Uniform8（round ties-to-even）；與 E07 的 multi-image/storyboard 兩份名單/PTS一致，8個不同 source frame、native PTS嚴格遞增。未看 GT event location 來取樣。這驗證的是**既有metadata一致性**，不是目前影片bytes或內容未變。

保留 source list 原始frame IDs/PTS，不從概略 half-open window boundary推導或補入未授權影格。test1/test7 的 first supplied frame可晚於概略左邊界一格；不自動補影格或改GT。native timestamp 不從nominal FPS或舊FFV1 AVI container PTS反推。

真實影片／PNG 完全未開啟；`recorded_source_png_sha256` 和 source-video SHA只沿用既有metadata，未fresh rehash。既有sampling manifest的 payload/chat hashes來自舊prompt，**不能**稱為本V1D最終18call hashes。若無法僅用metadata完成現行媒體校驗，維持 M01 UNVERIFIED，不能為此偷讀像素。舊REENCODED_AUTHORIZED_VIDEO mapping不是新native-array時間忠實性證據。

## Per-window selected frames and private temporal units

以下是 review/evaluation 私有mapping，不進模型prompt；不得把native PTS字串額外塞入V1D或加到storyboard。C3保留供應alias，report-only揭露每2影格一unit；不能把8alias誤稱8獨立video temporal units。

### test1__W03 / test1__W05 — PT2A_9d15d2a6b56b56d0

| alias | source frame | native PTS (s) | recorded source PNG SHA-256 |
| --- | --- | --- | --- |
| F0001 | S000157 | 5.235 | c96bcb3464d1345ba7168df8ff8837929a847b7eb83952aaa087737da6b7a407 |
| F0016 | S000172 | 5.736666666666666 | a423037171725e304306cbba99eb707117d2e5bb4a1a4f782858af48298c9376 |
| F0031 | S000187 | 6.236666666666666 | e67b0aab5587c12ed833390a39ab4d1fee5edfe73d6abc6f8f6248bff177ce78 |
| F0046 | S000202 | 6.736666666666666 | bf95a218f7ca83d04132a282c67c54ac5dddac6c7abf89ebb1f9efcc39dbf95d |
| F0062 | S000218 | 7.27 | c8c8249c52b055cbc00561cb1bc295264a0422458ee71ec3e6eaad3a72c43a23 |
| F0077 | S000233 | 7.77 | b7b6e79019122fff16fa390e7aa39fb439179c611e2aa62495314528ee28afc9 |
| F0092 | S000248 | 8.27 | ad3eedacb7b67c93f721174001742b85e557419955c4e4fb3a0308abd5de2e01 |
| F0107 | S000263 | 8.77 | dfc305263abf16f0d007b0ce50d1a09c8cf5d5e3d130edeebe1a5b2aabe0dc98 |

Uniform source positions: `[0, 15, 30, 45, 61, 76, 91, 106]`. Native-array nominal fps from source span: `1.9801980198019806`; seconds/unit: `1.0099999999999998`. These are source-code-derived candidate metadata, not a new processor receipt.

| unit | supplied alias pair | authoritative native PTS pair |
| --- | --- | --- |
| 0 | F0001, F0016 | [5.235, 5.736666666666666] |
| 1 | F0031, F0046 | [6.236666666666666, 6.736666666666666] |
| 2 | F0062, F0077 | [7.27, 7.77] |
| 3 | F0092, F0107 | [8.27, 8.77] |

### test2__W01 — PT2A_b35d807b28b92101

| alias | source frame | native PTS (s) | recorded source PNG SHA-256 |
| --- | --- | --- | --- |
| F0001 | S000180 | 6.008333333333334 | 4da2b477f51fc99a2480c4e423947ef7cd63c708546203a7720ee4f165880a79 |
| F0016 | S000195 | 6.51 | ff3e91a4a10081e00b9e6c23f3bf5773562e153309960812a820e5f7d11a7433 |
| F0032 | S000211 | 7.043333333333333 | 4e09d6211563fb9dc6b2f6254201be2a510a54d07327362042f2902c004cfca1 |
| F0047 | S000226 | 7.545 | 4f3c81a049380c89ea284bc7378943fbbe43c2119e1e7f815b3d8b29234455ef |
| F0062 | S000241 | 8.045 | c4c154354d592d988fcece8226fe5ad200419bfb7cb055474081fb20e2b3ba9b |
| F0077 | S000256 | 8.545 | 5104622569cf9a33399051cf37b6b9548a78ff4a4a6c8c10a842c6e639b4f70a |
| F0093 | S000272 | 9.08 | 527deef05ca17c4ac70357ed86a28cc47603f2cfaf99abfcd26fb31414d66949 |
| F0108 | S000287 | 9.58 | f529b360d0d340df4111375cebb0d74c104e2dca4dcdb9a6cdad67b5c1849ac9 |

Uniform source positions: `[0, 15, 31, 46, 61, 76, 92, 107]`. Native-array nominal fps from source span: `1.959869342043864`; seconds/unit: `1.0204761904761903`. These are source-code-derived candidate metadata, not a new processor receipt.

| unit | supplied alias pair | authoritative native PTS pair |
| --- | --- | --- |
| 0 | F0001, F0016 | [6.008333333333334, 6.51] |
| 1 | F0032, F0047 | [7.043333333333333, 7.545] |
| 2 | F0062, F0077 | [8.045, 8.545] |
| 3 | F0093, F0108 | [9.08, 9.58] |

### test5__W01 — PT2A_fe0910d66f4c5614

| alias | source frame | native PTS (s) | recorded source PNG SHA-256 |
| --- | --- | --- | --- |
| F0001 | S000162 | 5.4 | dc823f38acca0b7bec50d76c58a510b385664e069802a5b459b3137c40ebb866 |
| F0011 | S000172 | 5.733333333333333 | ff3dcaadb589f3ae0f4fbe46584d2f9c9fdb7898b0ae38bd11a3228e9687c606 |
| F0021 | S000182 | 6.066666666666666 | 373eba8e1f2c7e85a443da2bfafee0616e6f38ba1eda9d0bfaeb3bdae388acf9 |
| F0031 | S000192 | 6.4 | 585f0eb808d2533518d3f84b6e42009ea69da98476207baf5b63736b8754bc64 |
| F0042 | S000203 | 6.766666666666667 | 8046ec3e296eceb642e9813666900059c9c0f337055c27efb140798c81abe73b |
| F0052 | S000213 | 7.1 | 173fa0288e6b5ccb434a3f95e48085536d4b031eba979ea8d9baab9e5946778b |
| F0062 | S000223 | 7.433333333333334 | 9407cc5926117fd00844f8d343335cf476617e6602c66b4bbd6858cde979edd8 |
| F0072 | S000233 | 7.766666666666667 | 78d97a28db80f06ea186d6dbf5ddb2163a277f720afed0daf8af80233310d566 |

Uniform source positions: `[0, 10, 20, 30, 41, 51, 61, 71]`. Native-array nominal fps from source span: `2.95774647887324`; seconds/unit: `0.6761904761904761`. These are source-code-derived candidate metadata, not a new processor receipt.

| unit | supplied alias pair | authoritative native PTS pair |
| --- | --- | --- |
| 0 | F0001, F0011 | [5.4, 5.733333333333333] |
| 1 | F0021, F0031 | [6.066666666666666, 6.4] |
| 2 | F0042, F0052 | [6.766666666666667, 7.1] |
| 3 | F0062, F0072 | [7.433333333333334, 7.766666666666667] |

### test5__W05 — PT2A_eb60192e6986cb4f

| alias | source frame | native PTS (s) | recorded source PNG SHA-256 |
| --- | --- | --- | --- |
| F0001 | S000342 | 11.4 | 10cc01413d92bd21672cfb1c7310f4be4b1e1fac3ac6708d525981d7b96c9f27 |
| F0016 | S000357 | 11.9 | 220497de57fab64e8a6964fbc022a682b814c4e548063b5a6ee58c0fb0b77d82 |
| F0032 | S000373 | 12.433333333333334 | b2c53d6b0b61b8326bd06b1b6758e516b1f19d8f8b2442c01d9a5ddd540311e7 |
| F0047 | S000388 | 12.933333333333334 | 8fd6ad4e1602cbc458eb214dd9ac606861c769b4238bae45123bfc715dcfa08d |
| F0062 | S000403 | 13.433333333333334 | 03b066756b322b77d1f723a4b30e3b3f23013d92bc01da1fdc37f5f08e70a487 |
| F0077 | S000418 | 13.933333333333334 | ae177c755952014df4259765c76b0e25eeceb318c5800a785e72f177a9053794 |
| F0093 | S000434 | 14.466666666666667 | 48dccf469d84539f22e76a563f24337bcad2f91281103bd87d56c89e09584624 |
| F0108 | S000449 | 14.966666666666667 | a7d23c7026f542c956c4b745983eb1e92bf7c688e6341b9c7b8d934d7e8c862e |

Uniform source positions: `[0, 15, 31, 46, 61, 76, 92, 107]`. Native-array nominal fps from source span: `1.9626168224299068`; seconds/unit: `1.019047619047619`. These are source-code-derived candidate metadata, not a new processor receipt.

| unit | supplied alias pair | authoritative native PTS pair |
| --- | --- | --- |
| 0 | F0001, F0016 | [11.4, 11.9] |
| 1 | F0032, F0047 | [12.433333333333334, 12.933333333333334] |
| 2 | F0062, F0077 | [13.433333333333334, 13.933333333333334] |
| 3 | F0093, F0108 | [14.466666666666667, 14.966666666666667] |

### test7__W05 — PT2A_c58b4df88a2f6801

| alias | source frame | native PTS (s) | recorded source PNG SHA-256 |
| --- | --- | --- | --- |
| F0001 | S000373 | 12.435 | e7b2f09f119510a117c550138f5e8c659354f7f0df6ba737d2936b7e2a244ca1 |
| F0016 | S000388 | 12.935 | 4e8770c51400fa0105dcafd5b54b61826ba4417df99733b2eedce411e1dea8f7 |
| F0031 | S000403 | 13.436666666666667 | 5ec94a5b70fa68a9b144d78e94b3f0727c30944462adb6b3009bd3023a5acf67 |
| F0046 | S000418 | 13.936666666666667 | 12f6213b67ce89b8c300065de20809fc38c9963fe981fdbe95f8226d878cc43c |
| F0062 | S000434 | 14.471666666666666 | 7620fdb3160afaefcfb496588c2c2c3e084537e8d42c9c9d61453f334a219ba1 |
| F0077 | S000449 | 14.971666666666666 | a12f87d8dc22b55e7cee417cd2fc0a54b42cb7352646fc00b693087b653326d8 |
| F0092 | S000464 | 15.471666666666666 | 9305b535e199fca3dac5c12668c54a10910862c9fa5742441ca556d3aef6f11c |
| F0107 | S000479 | 15.973333333333333 | 6289ef44e2654d0d122724df72ba8b3fed75b41e84d8366723aa35d44b3b8eaa |

Uniform source positions: `[0, 15, 30, 45, 61, 76, 91, 106]`. Native-array nominal fps from source span: `1.9783325482807355`; seconds/unit: `1.0109523809523806`. These are source-code-derived candidate metadata, not a new processor receipt.

| unit | supplied alias pair | authoritative native PTS pair |
| --- | --- | --- |
| 0 | F0001, F0016 | [12.435, 12.935] |
| 1 | F0031, F0046 | [13.436666666666667, 13.936666666666667] |
| 2 | F0062, F0077 | [14.471666666666666, 14.971666666666666] |
| 3 | F0092, F0107 | [15.471666666666666, 15.973333333333333] |

### test8__W07 — PT2A_5dbb180e8ff88762

| alias | source frame | native PTS (s) | recorded source PNG SHA-256 |
| --- | --- | --- | --- |
| F0001 | S000936 | 31.211666666666666 | efd1101349c160f6e5f0cc090e040ee54776d25b74aa247fe2d55a56972b91ea |
| F0018 | S000953 | 31.78 | de8c2fc423fdcbf75a2712e948b535486383b0fe851186045232a9a5628d6201 |
| F0034 | S000969 | 32.31333333333333 | c247e1f263cbbd87a4826f836526ce1765f6cbe116f241d7cab05db1ea255f83 |
| F0051 | S000986 | 32.88166666666667 | 006ea90212bead15e710bf836e07538d36277ada7a563177b2d0dde20fed94aa |
| F0068 | S001003 | 33.44833333333333 | bf7b7b801cf9d3408e830859801c19b843ab2390091ceeaf3e82ea7bf62d8b6b |
| F0085 | S001020 | 34.0 | 7dd3100f769cd1236b77ed73bd915cf0a372b02419d12c5a06a13d85cc6aff6e |
| F0101 | S001036 | 34.53333333333333 | e2e6abc8591796ecb710790112c2706e161128220502f29b5e543268fd3035d6 |
| F0118 | S001053 | 35.10166666666667 | 4ef011631a8b9670114da16deee3a7d94edc3d04ce01a032cc5a9eac5dfadd1b |

Uniform source positions: `[0, 17, 33, 50, 67, 84, 100, 117]`. Native-array nominal fps from source span: `1.799485861182519`; seconds/unit: `1.1114285714285717`. These are source-code-derived candidate metadata, not a new processor receipt.

| unit | supplied alias pair | authoritative native PTS pair |
| --- | --- | --- |
| 0 | F0001, F0018 | [31.211666666666666, 31.78] |
| 1 | F0034, F0051 | [32.31333333333333, 32.88166666666667] |
| 2 | F0068, F0085 | [33.44833333333333, 34.0] |
| 3 | F0101, F0118 | [34.53333333333333, 35.10166666666667] |


完整metadata SHA和逐項核對見 FINAL_COMPONENT_HASH_MANIFEST.json 與 REVIEW_EVIDENCE_AND_PROPOSED_CONFIGURATION.json。
