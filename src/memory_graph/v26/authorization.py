"""Authorize irreversible identity actions only with observed uniqueness evidence."""
from __future__ import annotations

import copy


def authorize(scored, current_observation_ids, minimum_similarity=.60, minimum_margin=.10):
    """Wrap unchanged V2.4 scoring; absence of a competitor never proves uniqueness.

    A stale candidate cannot gain confirmation solely because a different phone
    appeared later. Both frozen appearance gates and a current observation of
    the winning candidate are required for irreversible authorization.
    """
    decisions = copy.deepcopy(scored)
    for row in decisions:
        base = row["decision"]
        score = row["appearance"]["max_similarity"]
        second = row.get("second_candidate_similarity")
        margin = row.get("best_vs_second_margin")
        if base == "REJECT":
            decision, reason = "REJECTED", "unchanged V2.4 hard contradiction"
        elif base == "MATCH" and score >= minimum_similarity:
            if second is None or margin is None:
                decision, reason = "PROVISIONAL_MATCH", "no eligible second candidate; uniqueness unproven"
            elif margin < minimum_margin:
                decision, reason = "AMBIGUOUS", "frozen uniqueness margin insufficient"
            elif row["candidate_entity_id"] not in current_observation_ids:
                decision, reason = "PROVISIONAL_MATCH", "stale candidate cannot gain confirmation from a later competitor"
            else:
                decision, reason = "CONFIRMED_MATCH", "frozen similarity and observed competitor margin pass"
        else:
            decision, reason = "AMBIGUOUS", "unchanged V2.4 scorer did not authorize match"
        row["v24_decision"] = base
        row["decision"] = decision
        row["v26_reason"] = reason
        allowed = decision == "CONFIRMED_MATCH"
        row["alias_authorized"] = allowed
        row["trusted_bank_update_authorized"] = allowed
        row["sam_reinitialization_authorized"] = allowed
    return decisions
