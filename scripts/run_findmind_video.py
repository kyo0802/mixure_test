"""One-command fresh MP4 processing or GPU-free persisted-session search."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]


def main():
    from memory_graph.integration.fresh_video import process_video,search_session
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--video');g.add_argument('--session')
    p.add_argument('--query',default='Where is my phone?')
    p.add_argument('--target-category',help='Optional explicit category for new video perception')
    p.add_argument('--entity-id',help='Existing independently authorized entity; never enrolls an identity')
    p.add_argument('--window-seconds',type=float,default=12)
    p.add_argument('--cv-fps',type=float,default=5)
    p.add_argument('--localization-budget',type=int,default=6)
    p.add_argument('--worker',choices=['cv','localization','sam'],help=argparse.SUPPRESS)
    a=p.parse_args()
    if a.worker:
        if not a.session:p.error('Worker requires --session')
        session=Path(a.session).resolve()
        if not session.is_relative_to(ROOT/'artifacts/findmind_sessions'):raise PermissionError('ISOLATED_SESSION_REQUIRED')
        from memory_graph.integration.fresh_workers import cv_worker,perception_worker
        if a.worker=='cv':cv_worker(ROOT,session)
        else:perception_worker(ROOT,session,a.worker)
        return
    if a.session:
        result=search_session(ROOT,Path(a.session),a.query,a.entity_id)
    else:
        if a.entity_id:p.error('Fresh videos have no enrollment. --entity-id is query-only.')
        _,result=process_video(ROOT,a.video,a.query,a.target_category,a.window_seconds,a.cv_fps,a.localization_budget)
    # Full results are preserved on disk; terminal keeps a readable top-five view.
    print(json.dumps(dict(status=result['status'],query=a.query,session=result['session_id'],
        candidates_total=len(result['candidates']),candidates=[dict(location=c.get('location_label'),
            native_pts_s=c['source_time_s'],frame=c['source_frame_index'],bbox=c.get('object_bbox'),
            identity=c['identity_scope'],relation=c['spatial_relation'],uncertainty=c['uncertainty'],
            evidence=c.get('source_frame')) for c in result['candidates'][:5]],
        incomplete_stages=result['incomplete_stages'],models_loaded_for_query=False),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
