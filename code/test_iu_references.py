"""Synthetic, source-text-free fixtures for lossless nested JSON references."""
import json
import re
import unittest
from iu_references import IUReferences

class NestedJSON(unittest.TestCase):
    def setUp(self):
        self.codec = IUReferences([{'doc_id':'example','text':'A fictional blue triangle is here. A red square follows.'}])

    def test_short_serialized_surface(self):
        raw = json.dumps({'entities':[{'text':'blue','start':12,'end':16}]})
        encoded = self.codec.encode(raw)
        self.assertEqual(self.codec.decode(encoded), raw)
        self.assertNotIn('blue', json.dumps(encoded))

    def test_whitespace_exactly_preserved(self):
        raw = '{\n "entities": [ {"text" : "red square", "start": 36} ]\n}'
        encoded = self.codec.encode(raw)
        self.assertEqual(self.codec.decode(encoded), raw)
        self.assertNotIn('red square', json.dumps(encoded))

    def test_unknown_text_is_not_fabricated(self):
        raw = '{"text":"invented-blue"}'
        encoded = self.codec.encode(raw)
        self.assertEqual(self.codec.decode(encoded), raw)
        self.assertIn('invented', json.dumps(encoded))
        self.assertNotIn('blue', json.dumps(encoded))

    def test_indexed_report_is_not_literal(self):
        source = self.codec.reports['example']
        indexed = ' '.join(f'[{m.start()}:{m.end()}]{m.group()}' for m in re.finditer(r'\S+', source))
        encoded = self.codec.encode({'target_offset_reference': indexed})
        self.assertEqual(self.codec.decode(encoded), {'target_offset_reference': indexed})
        self.assertNotIn('triangle', json.dumps(encoded))
        self.assertNotIn('square', json.dumps(encoded))

    def test_single_character_structured_surface(self):
        value={'entities':[{'text':'A','start':0,'end':1}]}
        encoded=self.codec.encode(value)
        self.assertEqual(self.codec.decode(encoded),value)
        self.assertIsInstance(encoded['entities'][0]['text'],dict)

    def test_serialized_indexed_report(self):
        source = 'A fictional "blue" triangle.\nA red square.'
        codec = IUReferences([{'doc_id':'example','text':source}])
        indexed = ' '.join(f'[{m.start()}:{m.end()}]{m.group()}' for m in re.finditer(r'\S+', source))
        raw = json.dumps({'target_offset_reference':indexed})
        encoded = codec.encode(raw)
        self.assertEqual(codec.decode(encoded), raw)
        self.assertNotIn('triangle', json.dumps(encoded))
        self.assertNotIn('square', json.dumps(encoded))

if __name__ == '__main__':
    unittest.main()
