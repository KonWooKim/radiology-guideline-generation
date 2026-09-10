"""Restore source, inputs and saved outputs into a PRIVATE working directory."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from iu_references import IUReferences, verified_reports, serialize

ROOT = Path(__file__).resolve().parents[1]


def open_records(path):
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8')
    return path.open('r', encoding='utf-8')


def package_files(bundle_dir):
    index_path = bundle_dir/'index.jsonl'
    if index_path.exists():
        if list(bundle_dir.glob('*.gz')):
            raise ValueError('Do not mix plain and compressed reconstruction formats')
        index = [json.loads(line) for line in index_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        files = sorted(p for p in bundle_dir.glob('*.jsonl') if p != index_path)
    else:
        index_path = bundle_dir/'index.json.gz'
        index = json.loads(gzip.decompress(index_path.read_bytes()))
        files = sorted(bundle_dir.glob('*.jsonl.gz'))
    return index_path, index, files


def safe_path(root, name):
    """Accept only portable relative paths, including when run on POSIX."""
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Unsafe archive path')
    parts = name.split('/')
    if any(p in {'', '.', '..'} or p.endswith((' ', '.')) for p in parts):
        raise ValueError('Unsafe archive path')
    if PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive:
        raise ValueError('Unsafe archive path')
    if any(PureWindowsPath(p).is_reserved() for p in parts):
        raise ValueError('Reserved archive path')
    out = (root/name).resolve()
    if root not in out.parents:
        raise ValueError('Unsafe archive path')
    return out


def preflight(root, target):
    """Verify archives and their complete index before writing restored files."""
    bundle_dir = root/'reproduction'
    manifest = json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    hashes = {r['path']: r['sha256'] for r in manifest['files']}
    index_path, index, files = package_files(bundle_dir)
    for file in [index_path, *files]:
        key = file.relative_to(root).as_posix()
        if hashlib.sha256(file.read_bytes()).hexdigest() != hashes.get(key):
            raise ValueError('Archive checksum mismatch: '+key)
    expected = {}
    destinations = set()
    for row in index:
        dest = safe_path(target, row['path']).as_posix().casefold()
        if row['path'] in expected or dest in destinations:
            raise ValueError('Duplicate archive destination')
        destinations.add(dest)
        expected[row['path']] = row
    seen = set()
    for archive in files:
        with open_records(archive) as stream:
            for line in stream:
                record = json.loads(line)
                path = record['path']
                header = {k:v for k,v in record.items() if k != 'payload'}
                header['archive'] = archive.name
                if path in seen or expected.get(path) != header:
                    raise ValueError('Archive/index mismatch: '+path)
                if record['kind'] not in {'text', 'json', 'jsonl'}:
                    raise ValueError('Unsupported record kind')
                seen.add(path)
    if seen != set(expected):
        raise ValueError('Incomplete reconstruction archives')
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    target = a.output.resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError('Restore outside the public repository to prevent accidental redistribution')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError('Use an empty output directory. Existing results are never overwritten')
    archives = preflight(ROOT, target)
    codec = IUReferences(verified_reports(a.reports, ROOT/'annotations/reference.jsonl'))
    count = 0
    for archive in archives:
        with open_records(archive) as f:
            for line in f:
                r = json.loads(line)
                out = safe_path(target, r['path'])
                value = codec.decode(r['payload'])
                text = serialize(value, r['kind'], r.get('format'))
                if hashlib.sha256(text.encode()).hexdigest() != r['restored_sha256']:
                    raise ValueError('Restoration mismatch: '+r['path'])
                # Historical absolute paths are metadata, not executable path defaults.
                # Relocate only the documented study-root token.
                text = text.replace('${STUDY_ROOT}', target.as_posix())
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding='utf-8', newline='')
                count += 1
    print(json.dumps({'restored_files': count, 'output': str(target), 'API_calls': 0,
                      'author_manual_included': False}))


if __name__ == '__main__':
    main()
