# V1C prompt追溯 — 尚未批准

| Step0 category | 原contract | 新clarification | 證據 | 風險 |
|---|---|---|---|---|
| 空timing，13attempt/18欄位 | 每event string minLength1 | exact/bounded/unknown的非空誠實文字，不能造精確時間 | schema與diagnostics/frequencies.json | 可能改uncertainty措辭，尚未測效能 |
| 空window cite，5attempt | 所有四種outcome都minItems1 | 依outcome引用支持或不足的實際影格，不造alias | 原schema/validator | 引用valid不代表grounding或continuousassessability |
| known-state無support，11attempt/20欄位 | known requires alias，unknown requires null | before/after/last均遵循；看得見不等於held | shadow原碼規則+JSONL | 可能增加UNKNOWN，不證明提升事件辨識 |

原task完整保留，只追加抽象規則；沒有full-schema示例、fixture-specific例子或答案。pending identity clause完全獨立。沒有新增mandatoryfields、enum、timestamps；沒有強迫exacttime、事件數、隱藏狀態或持續性。

候選SHA `3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722`；原taskSHA `94b52f47e965691e01f85012ab0c8ad7653271c4fa229222ba190f2d6eabf679`；V2systemSHA `9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e`。token count={'status': 'EXACT', 'token_count': 659, 'scope': 'standalone task prompt, excludes system/schema/media/template expansion', 'tokenizer_class': 'Qwen2TokenizerFast', 'transformers_version': '4.57.6', 'torch_version': '2.10.0+cu128', 'cuda_initialized': False}。只計task本體，不能當實際expandedinputtokens。

鎖回條hash `149f8696e51fa91cf43147d761315672dc43594aebe41b58cea8ed78956346ee` 被prompt receipt引用；lock自身指向immutablemanifest/影格hash且記錄prompt absent，Step0B完成後才寫candidate。時間戳只是補充。作者知道fixtures概念，這不證明概念盲測。

保留規則：Prediction V1、parser/validator、V2formatting、V3construction/runtime、greedy等全部不改。尚未釐清target-NONE的科學解讀、Video可辨alias粒度與citation/abstention真正衝突；均交human，不以修schema提高舊pass率。
