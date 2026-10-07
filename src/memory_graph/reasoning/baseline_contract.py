"""Seven fields; no examples, numbered evidence, physical gate or citations."""
from .json_contract import parse_json

KEYS={'event_type','interaction_anchor','released','target_visible_after','final_relation','final_relation_anchor','confidence'}
EVENT_TYPES=('STATIC','PICKED_UP','CARRIED_OR_HELD','PLACED_OR_PUT_DOWN','BECAME_OCCLUDED','REAPPEARED','NO_CLEAR_INTERACTION','UNCERTAIN')
RELATIONS=('ON','INSIDE','BEHIND','OCCLUDED_BY','NEAR','HELD_BY','NONE','UNCERTAIN')

def prompt(event):
    markers=', '.join(event['markers'])
    phases=', '.join(f['phase'] for f in event['frames'])
    return f'''Interpret the dominant observable event involving marked target T over the chronological visual sequence.
T identity is already assigned upstream. Follow only T, never another visible phone/device. Do not identify or rename T.
Supplied candidate context markers: {markers}. They are not necessarily interacting entities.
Use NONE when the actual interacting entity is unmarked or no supplied anchor interacts; never force a marker or invent an entity.
Image phases in order: {phases}. Same-image reference panels repeat that image.
Return only one JSON object with exactly these keys: event_type, interaction_anchor, released, target_visible_after, final_relation, final_relation_anchor, confidence.
event_type: {' / '.join(EVENT_TYPES)}. Select the dominant event; STATIC means stationary, CARRIED_OR_HELD does not establish final placement.
interaction_anchor and final_relation_anchor: {markers}, NONE, UNCERTAIN.
released: YES / NO / UNCERTAIN. YES requires observed release or put-down, never mere loss of visibility or an AFTER phase.
target_visible_after: YES / PARTIAL / NO / UNCERTAIN, describing only the final supplied view; NO does not establish physical absence.
final_relation: {' / '.join(RELATIONS)}. State only supported final relations; NEAR is not a fallback for scene co-presence.
For NONE relation use NONE anchor; for UNCERTAIN relation use NONE or UNCERTAIN anchor.
confidence: HIGH / MEDIUM / LOW, diagnostic only.
Use NONE for no meaningful supplied relation and UNCERTAIN for insufficient evidence. No other keys, prose, or reasoning explanation.'''
