# V1D schema field audit

已從12份舊raw JSON、schema error paths、原schema與Validator核對，global欄位是根物件的 **`uncertainty`，JSON path `/uncertainty`**；required string、non-null、minLength1，四種outcome皆適用。舊6份SCHEMA_MINLENGTH確實來自這個path，不是target_association_uncertainty(enum)，也不是event timing_uncertainty。

Event：`/events/*/timing_uncertainty`，每個實際存在event required string/non-null/minLength1；零event時不適用。Timing可EXACT_SUPPLIED_FRAME、BOUNDED_SUPPLIED_FRAMES或TIMING_UNKNOWN，非一律兩個bounding frames。Schema只檢查字串長度，描述是否有意義／有視覺支持需另審，不能用無意義文字充數。

Window citations：`/window_cited_frame_aliases` required array/minItems1/uniqueItems，item pattern `^F[0-9]{4}$`。CONFIRMED_EVENTS、NO_CONFIRMED_EVENT、INSUFFICIENT_EVIDENCE、TARGET_NOT_OBSERVABLE全部都要求，沒有conditional exception。Validator再核對processor-consumed alias membership；event cited_frame_aliases另有minItems1。靜態reference非event證據，未處理clip frames／private IDs不能引用。Citation不是連續assessability證明。

Semantic precheck通過：可描述真正直接觀察的取樣解析度、真實前後觀察缺口、未知時間或實際遮擋；沒有額外觀察到的限制也可在現有observations範圍說明。不可捏造遮擋／interval／midpoint；before/after bracket不是物理動作duration。沒有內部矛盾要求停工。Strict Validator/schema/parser均不修改；歷史raw只用於本稽核，未搬入新prompt。
