"""Prepare a local private DPCP index from the user's existing extracted texts."""
import argparse
import hashlib
import json
from pathlib import Path


def chunks(text, size=1800):
    lines = text.splitlines()
    start, contents, count = 1, [], 0
    for number, line in enumerate(lines, 1):
        # Worksheet formulas are not quality requirements. Keep the other cells
        # and the original line numbering, so citations remain traceable.
        cells = line.split(' | ')
        line = ' | '.join(cell for cell in cells
                          if not cell.lstrip().startswith('=') and '__xludf' not in cell).strip(' |')
        if contents and count + len(line) > size:
            yield start, number - 1, '\n'.join(contents)
            start, contents, count = number, [], 0
        # Preserve unusually long source rows in bounded pieces with the same line locator.
        if len(line) > 6000:
            for offset in range(0, len(line), size):
                yield number, number, line[offset:offset+size]
            start = number + 1
        else:
            contents.append(line)
            count += len(line) + 1
    if contents:
        yield start, len(lines), '\n'.join(contents)


def build(roots, destination):
    records, files, unavailable = [], [], []
    for root in roots:
        for path in sorted(Path(root).glob('*.txt')):
            if path.name.upper().startswith('ARCHIVE'):
                continue
            # A dataless iCloud file is not a readable source. Do not silently index nothing.
            if getattr(path.stat(), 'st_flags', 0) & 0x40000000:
                unavailable.append(str(path))
                continue
            text = path.read_text(encoding='utf-8').strip()
            if not text:
                unavailable.append(str(path))
                continue
            title = path.stem.replace('___', ' — ').replace('__', ' ').replace('_', ' ')
            digest = hashlib.sha256(text.encode()).hexdigest()
            count = 0
            for first, last, content in chunks(text):
                if content.strip():
                    records.append({'title': title, 'source': path.name,
                        'locator': f'{path.name} · lines {first}–{last}', 'content': content,
                        'source_sha256': digest, 'archived': False})
                    count += 1
            files.append({'file': path.name, 'sha256': digest, 'chunks': count})
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if not records:
        (destination / 'ingestion-status.json').write_text(json.dumps({'available': False,
            'documents': [], 'unavailable': unavailable}, ensure_ascii=False, indent=2))
        raise RuntimeError(f'No readable DPCP source documents; {len(unavailable)} unavailable files')
    (destination / 'index.jsonl').write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in records) + '\n')
    (destination / 'ingestion-status.json').write_text(json.dumps({'available': True, 'documents': files,
        'chunks': len(records), 'unavailable': unavailable}, ensure_ascii=False, indent=2))
    return len(files), len(records), len(unavailable)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', action='append', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(build(args.source, args.output))
