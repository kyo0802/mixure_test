"""Owner-only media verification and zero-dependency reviewer ZIP builder."""
import argparse
import json
import shutil
import sys
import zipfile
import html
import re
from pathlib import Path
from findmind_gt_contract import ROOT, TOOL, annotation_schema, canonical, digest, file_sha, load_json

def write_readable_guide():
    """Render the bundled, trusted reviewer notes into a directly readable local page."""
    def inline(s):
        s=html.escape(s)
        s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
        links={'README.md':'#start','ANNOTATION_GUIDE.md':'#rules','MANUAL_ACCEPTANCE.md':'#acceptance'}
        for filename,anchor in links.items():
            s=re.sub(r'\[([^\]]+)\]\('+re.escape(filename)+r'\)',lambda m:'<a href="'+anchor+'">'+m.group(1)+'</a>',s)
        return s
    chunks=[]
    for filename,anchor in [('README.md','start'),('ANNOTATION_GUIDE.md','rules'),('MANUAL_ACCEPTANCE.md','acceptance')]:
        chunks.append('<section id="'+anchor+'">')
        for block in (TOOL/filename).read_text(encoding='utf8').split('\n\n'):
            if not block.strip():continue
            if block.startswith('#'):
                match=re.match(r'^(#{1,4})\s+(.+)',block);level=len(match[1]);chunks.append(f'<h{level}>'+inline(match[2])+f'</h{level}>')
            else:chunks.append('<p>'+inline(block).replace('\n','<br>')+'</p>')
        chunks.append('</section><hr>')
    (TOOL/'guide.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>FindMind 使用與標註說明</title><link rel="stylesheet" href="style.css"><body><article class="welcome"><p><a href="index.html">回到標註工具</a></p>'+''.join(chunks)+'</article></body></html>',encoding='utf8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip-only', action='store_true', help='Repackage existing verified media without decoding again')
    args = parser.parse_args()
    TOOL.mkdir(parents=True, exist_ok=True)
    if not args.zip_only:
        sys.path.insert(0, str(ROOT/'outputs/current_development/video_event_experiment/.deps'))
        import av
        ds = load_json(ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1/dataset.json')
        videos = []
        (TOOL/'videos').mkdir(exist_ok=True)
        for entry in ds['videos']:
            source = ROOT/(entry['video_id']+'.mp4')
            original_sha = file_sha(source)
            if original_sha != entry['sha256']: raise ValueError('Source changed: ' + source.name)
            with av.open(str(source)) as container:
                stream = container.streams.video[0]
                if stream.codec_context.name != 'h264' or stream.codec_context.format.name != 'yuv420p':
                    raise ValueError('Requires explicitly mapped browser preview encoding: ' + source.name)
                frames = [{'index': i, 'pts': f.pts, 'source_time_s': float(f.pts*f.time_base), 'duration_s': float(f.duration*f.time_base)} for i, f in enumerate(container.decode(stream))]
                if not frames or frames[0]['source_time_s'] != 0: raise ValueError('Nonzero source origin needs mapping')
                duration = frames[-1]['source_time_s'] + frames[-1]['duration_s']
                if len(frames) != entry['frame_count'] or abs(duration-entry['duration_seconds']) > 1e-6: raise ValueError('Timeline differs')
                preview = TOOL/'videos'/source.name
                if not preview.exists() or file_sha(preview) != original_sha: shutil.copyfile(source, preview)
                if file_sha(preview) != original_sha: raise ValueError('Copy hash mismatch')
                videos.append({'video_id': entry['video_id'], 'original_filename': source.name, 'source_sha256': original_sha,
                    'source_duration_s': duration, 'fps': float(stream.average_rate), 'frame_count': len(frames),
                    'time_base': str(stream.time_base), 'width': stream.width, 'height': stream.height,
                    'codec': 'h264', 'pixel_format': 'yuv420p', 'preview_path': 'videos/'+source.name,
                    'preview_sha256': original_sha, 'preview_duration_s': duration, 'bytes': source.stat().st_size,
                    'time_mapping': {'kind': 'BYTE_IDENTICAL_SOURCE_MP4', 'offset_s': 0, 'source_origin_s': 0},
                    'frame_timeline': frames})
            print('VERIFIED', source.name, len(frames), flush=True)
        manifest = {'dataset_id': 'findmind_test1_test9', 'dataset_version': 'original9_nativepts_v1',
                    'timing_precision': 'HTML5_TIMESTAMP_APPROXIMATE', 'videos': videos}
        manifest['dataset_manifest_sha256'] = digest(manifest)
        (TOOL/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
        (TOOL/'manifest.js').write_text('window.FINDMIND_MANIFEST = '+canonical(manifest)+';\n', encoding='utf8')
        schema = annotation_schema()
        (TOOL/'schema.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf8')
        (TOOL/'schema.js').write_text('window.FINDMIND_SCHEMA = '+canonical(schema)+';\n', encoding='utf8')
    manifest = load_json(TOOL/'manifest.json')
    content = {k:v for k,v in manifest.items() if k != 'dataset_manifest_sha256'}
    if digest(content) != manifest['dataset_manifest_sha256']: raise ValueError('Manifest hash mismatch')
    for v in manifest['videos']:
        if file_sha(TOOL/v['preview_path']) != v['preview_sha256']: raise ValueError('Packaged media changed')
    write_readable_guide()
    required = ['index.html','style.css','app.js','contract.js','manifest.js','manifest.json','schema.js','schema.json','guide.html','README.md','ANNOTATION_GUIDE.md','MANUAL_ACCEPTANCE.md']
    missing = [p for p in required if not (TOOL/p).is_file()]
    if missing: raise ValueError('Missing application files: '+str(missing))
    dist = ROOT/'dist';dist.mkdir(exist_ok=True)
    target = dist/'findmind-gt-annotator.zip'
    entries = [TOOL/p for p in required] + [TOOL/v['preview_path'] for v in manifest['videos']]
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for p in entries: archive.write(p, Path('findmind-gt-annotator')/p.relative_to(TOOL))
    print(json.dumps({'videos': len(manifest['videos']), 'media_bytes': sum(v['bytes'] for v in manifest['videos']), 'folder_bytes': sum(p.stat().st_size for p in entries), 'zip_bytes': target.stat().st_size, 'zip_sha256': file_sha(target), 'manifest_sha256': manifest['dataset_manifest_sha256']}, indent=2))

if __name__ == '__main__': main()
