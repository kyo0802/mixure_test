"""English prompt, following the actual frozen canonical seven-field contract."""
from memory_graph.reasoning.contract import EVENT_TYPES, RELATIONS

TEMPLATE = '''Read these separate images chronologically: BEFORE -> TRANSITION -> AFTER.
Reason only about cyan marked target T. Its identity is authorized upstream; do not identify, rename, or substitute another phone. A missing T marker means identity is not authorized in that frame. Same-frame reference crops repeat that image, not additional time steps.
Distinguish genuine target movement from camera motion and detector box jitter. Look for approach, contact, target starting to move, movement together with an actor, reaching a destination, stopping, changed support, hand withdrawal, and whether T remains behind. Nearby hands alone do not establish an action. Grasping, turning, or flipping T is handling even without a large translation; if the hand continues to visibly grip T, use CARRIED_OR_HELD. A visibly held target is CARRIED_OR_HELD even if stationary relative to its holder or camera. STATIC means resting without observable handling or physical change.
Determine the final state from the last supplied images, not an intermediate frame. Placement/release needs a supported transfer or stop followed by hand/actor withdrawal with T remaining, or another visible release. A target may already contact a surface while still gripped: fingers disengaging and withdrawing while T stays on that surface is observed release, even without a visible drop or large movement. Classify this supported end-of-handling transition as PLACED_OR_PUT_DOWN, released YES. Continuing grip at the end means no observed release. Visibility loss is not release. An incomplete or very short sequence does not justify extrapolating a before/after transition: state only directly visible holding/resting, otherwise UNCERTAIN. Resolve insufficient evidence by abstaining, rather than repeatedly reconsidering an unobservable action. Do not invent support, containment, behind, proximity, or an interacting entity. Candidate boxes are hints, never mandatory answers; nearest is not necessarily final anchor. A visible but unmarked supporting surface cannot become an invented anchor; final_relation NONE is allowed even when the action is clear.
Return only one JSON object with exactly: event_type, interaction_anchor, released, target_visible_after, final_relation, final_relation_anchor, confidence.
event_type: {events}.
interaction_anchor: {anchors}. It expresses actor attribution where a supplied actor actually interacts; use NONE if unmarked or absent, UNCERTAIN if unresolved.
released: YES / NO / UNCERTAIN. YES only for observed release. STATIC cannot have released YES. PLACED_OR_PUT_DOWN cannot have released NO.
target_visible_after: YES / PARTIAL / NO / UNCERTAIN, restricted to the supplied end view. An unmarked lookalike does not establish T visibility or identity.
final_relation: {relations}. Only supported relations at the end; NEAR is not mere co-presence. HELD_BY requires visible holding and an actor marker, PICKED_UP or CARRIED_OR_HELD, released not YES, and the same interaction anchor.
final_relation_anchor: {anchors}. For NONE relation use NONE; for UNCERTAIN relation use NONE or UNCERTAIN. All other relations require a supplied marker visibly supporting that relation.
confidence: HIGH / MEDIUM / LOW (diagnostic only).
Actor hints: {actors}. Location hints: {locations}. Detector descriptions (fallible candidate hints): {descriptions}. Ordered phases: {phases}.
No additional keys, prose, or reasoning explanation.'''

def prompt(event):
    return TEMPLATE.format(events=' / '.join(EVENT_TYPES), relations=' / '.join(RELATIONS),
                           anchors=' / '.join(event['markers']+['NONE', 'UNCERTAIN']),
                           actors=', '.join(event.get('actor_markers', [])) or 'NONE',
                           locations=', '.join(event.get('location_markers', [])) or 'NONE',
                           descriptions=', '.join(f"{c['marker']}={c['raw_label']}" for c in event.get('contexts', [])) or 'NONE',
                           phases=', '.join(f['phase'] for f in event['frames']))
