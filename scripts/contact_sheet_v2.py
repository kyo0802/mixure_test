"""Create paginated event contact sheets for manual review, without altering VLM inputs."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def contact_sheets(output):
    output = Path(output)
    ids = json.loads((output/'active_event_ids.json').read_text())
    for offset in range(0,len(ids),4):
        page = Image.new('RGB',(1440,4*310),(245,245,245))
        draw = ImageDraw.Draw(page)
        for row, event_id in enumerate(ids[offset:offset+4]):
            directory = output/'events'/event_id
            event = json.loads((directory/'event.json').read_text())
            draw.text((10,row*310+4),f"{event_id} | {event['peak_time']:.2f}s | {', '.join(event['signals'])}",fill='black')
            for col, phase in enumerate(['before','during','after']):
                with Image.open(directory/f'{phase}.jpg') as image:
                    image.thumbnail((480,270))
                    page.paste(image,(col*480,row*310+30))
        path = output/f'event_contact_sheet_{offset//4+1:02d}.jpg'
        page.save(path,quality=92)
        print(path.resolve())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('outputs',nargs='+')
    for output in parser.parse_args().outputs:
        contact_sheets(output)
