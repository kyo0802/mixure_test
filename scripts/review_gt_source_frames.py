"""Extract chronological source frames for explicit visual review; no model calls."""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs/current_development/video_event_experiment/.deps'))
import av
from PIL import Image, ImageDraw
sys.path.insert(0, str(ROOT / 'scripts'))
from findmind_gt_contract import load_json, file_sha

OUT = ROOT / 'artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence'


def extract(video, start, end, step, label, width=480, columns=4, rows=3):
    manifest = load_json(ROOT / 'tools/findmind-gt-annotator/manifest.json')
    meta = next(v for v in manifest['videos'] if v['video_id'] == video)
    path = ROOT / meta['original_filename']
    assert file_sha(path) == meta['source_sha256']
    dest = OUT / label; dest.mkdir(parents=True, exist_ok=False)
    selected, images = [], []; next_time = start
    end = min(end, meta['source_duration_s'])
    with av.open(str(path)) as container:
        for index, frame in enumerate(container.decode(video=0)):
            t = float(frame.pts * frame.time_base)
            if t > end + .04: break
            if t + 1e-9 < next_time: continue
            if t < start: continue
            im = frame.to_image().convert('RGB')
            h = round(im.height * width / im.width)
            images.append(im.resize((width, h)))
            selected.append({'source_frame_index': index, 'native_pts_s': t, 'native_pts': frame.pts, 'time_base': str(frame.time_base)})
            next_time += step
    page_size = columns * rows; pages = []
    for offset in range(0, len(images), page_size):
        batch = images[offset:offset + page_size]; h = batch[0].height
        sheet = Image.new('RGB', (columns * width, rows * (h + 29)), '#eeeeee'); draw = ImageDraw.Draw(sheet)
        for i, im in enumerate(batch):
            x, y = i % columns * width, i // columns * (h + 29); info = selected[offset + i]
            draw.text((x + 6, y + 5), f"{video} | {info['native_pts_s']:.3f}s | f{info['source_frame_index']}", fill='black')
            sheet.paste(im, (x, y + 29))
        filename = f'page_{offset // page_size + 1:02d}.jpg'; sheet.save(dest / filename, quality=95)
        pages.append({'path': str((dest / filename).relative_to(ROOT)), 'frames': selected[offset:offset + page_size]})
    (dest / 'source_frames.json').write_text(json.dumps({'video': video, 'source_sha256': meta['source_sha256'], 'start_s': start, 'end_s': end, 'sampling_step_s': step,
        'method': 'First native frame at or after each requested source timestamp; chronological original frames, no model overlays.', 'pages': pages}, indent=2), encoding='utf-8')
    return {'label': label, 'frames': len(selected), 'pages': [p['path'] for p in pages]}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--video', required=True); p.add_argument('--start', type=float, default=0); p.add_argument('--end', type=float, default=999)
    p.add_argument('--step', type=float, default=1); p.add_argument('--label', required=True); p.add_argument('--width', type=int, default=480)
    p.add_argument('--columns', type=int, default=4); p.add_argument('--rows', type=int, default=3)
    a = p.parse_args(); assert a.step > 0
    print(json.dumps(extract(a.video, a.start, a.end, a.step, a.label, a.width, a.columns, a.rows)))


if __name__ == '__main__': main()
