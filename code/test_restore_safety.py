"""Offline tests of archive validation. Synthetic fixtures only, no IU data."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from restore_study import preflight, safe_path


class RestoreSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.target = self.root/'private'
        (self.root/'reproduction').mkdir()
        self.record = {'path':'scripts/example.py', 'kind':'text',
                       'source_sha256':'unused',
                       'restored_sha256':hashlib.sha256(b'# synthetic fixture\n').hexdigest(),
                       'payload':'# synthetic fixture\n'}

    def fixture(self, records=None, index=None):
        records = records if records is not None else [self.record]
        index = index if index is not None else [
            {**{k:v for k,v in r.items() if k != 'payload'}, 'archive':'test-001.jsonl.gz'} for r in records]
        paths = {'reproduction/test-001.jsonl.gz': ''.join(json.dumps(r)+'\n' for r in records).encode(),
                 'reproduction/index.json.gz':json.dumps(index).encode()}
        files = []
        for name, data in paths.items():
            blob = gzip.compress(data, mtime=0)
            (self.root/name).write_bytes(blob)
            files.append({'path':name, 'sha256':hashlib.sha256(blob).hexdigest()})
        (self.root/'MANIFEST.json').write_text(json.dumps({'files':files}))

    def test_valid_bundle(self):
        self.fixture()
        self.assertEqual(len(preflight(self.root, self.target)), 1)

    def plain_fixture(self):
        index=[{**{k:v for k,v in self.record.items() if k!='payload'},'archive':'test-001.jsonl'}]
        files={'reproduction/test-001.jsonl':json.dumps(self.record)+'\n',
               'reproduction/index.jsonl':json.dumps(index[0])+'\n'}
        manifest=[]
        for name,text in files.items():
            data=text.encode()
            (self.root/name).write_bytes(data)
            manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
        (self.root/'MANIFEST.json').write_text(json.dumps({'files':manifest}))

    def test_valid_plain_bundle(self):
        self.plain_fixture()
        self.assertEqual(len(preflight(self.root,self.target)),1)

    def test_mixed_formats_rejected(self):
        self.fixture()
        self.plain_fixture()
        with self.assertRaisesRegex(ValueError,'mix'):
            preflight(self.root,self.target)

    def test_unsafe_paths(self):
        for path in ['../escape', '/absolute', 'C:/outside', 'C:relative',
                     'folder\\escape', 'folder//empty', './dot', 'folder/../escape',
                     'NUL', 'folder/CON.txt', 'folder/file:stream', 'folder/trailing.']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_path(self.target, path)

    def test_archive_tampering(self):
        self.fixture()
        archive = self.root/'reproduction/test-001.jsonl.gz'
        archive.write_bytes(archive.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            preflight(self.root, self.target)

    def test_missing_record(self):
        self.fixture()
        index = json.loads(gzip.decompress((self.root/'reproduction/index.json.gz').read_bytes()))
        self.fixture(records=[], index=index)
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            preflight(self.root, self.target)

    def test_duplicate_destination(self):
        self.fixture(records=[self.record, self.record])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            preflight(self.root, self.target)

    def test_case_collision(self):
        self.fixture(records=[self.record, {**self.record, 'path':'Scripts/Example.py'}])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            preflight(self.root, self.target)

    def test_index_disagreement(self):
        self.fixture(index=[])
        with self.assertRaisesRegex(ValueError, 'index mismatch'):
            preflight(self.root, self.target)


if __name__ == '__main__':
    unittest.main()
