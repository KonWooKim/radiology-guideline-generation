"""Lossless text references to a separately obtained, hash-checked IU corpus.

No network, dependencies, or model calls. Reference offsets index the named
representation of the report (plain text unless form is explicitly specified).
"""
import hashlib
import json
import re
from functools import lru_cache


def serialize(value, kind, fmt=None):
    if kind == 'text':
        return value
    fmt = fmt or {'compact': True, 'ascii': False, 'indent': None, 'tail': '\n', 'newline':'\n', 'bom':False}
    kw = {'ensure_ascii':fmt['ascii'], 'indent':fmt['indent']}
    if fmt['compact']:
        kw['separators'] = (',', ':')
    if kind == 'jsonl':
        text = '\n'.join(json.dumps(x, **kw) for x in value)
    else:
        text = json.dumps(value, **kw)
    text = text.replace('\n', fmt['newline'])+fmt['tail']
    return ('\ufeff' if fmt['bom'] else '')+text


class IUReferences:
    def __init__(self, reports):
        self.reports = {str(r['doc_id']): r['text'] for r in reports}
        self.forms = {}
        self.index = {}
        for doc, text in self.reports.items():
            indexed = ' '.join(f'[{m.start()}:{m.end()}]{m.group()}' for m in re.finditer(r'\S+', text))
            for form, value in [('plain', text), ('json', json.dumps(text, ensure_ascii=False)[1:-1]),
                                ('ascii', json.dumps(text, ensure_ascii=True)[1:-1]),
                                ('lower',text.lower()),('upper',text.upper()),
                                ('indexed', indexed),
                                ('indexed_json', json.dumps(indexed, ensure_ascii=False)[1:-1]),
                                ('indexed_ascii', json.dumps(indexed, ensure_ascii=True)[1:-1])]:
                self.forms[doc, form] = value
                tokens = list(re.finditer(r'\w+', value))
                for i in range(len(tokens)-2):
                    key = tuple(t.group() for t in tokens[i:i+3])
                    self.index.setdefault(key, []).append((doc, form, tokens[i].start()))

    @lru_cache(maxsize=100000)
    def encode_surface(self, value):
        """Reference source words even inside a JSON-serialized text field."""
        if not value:
            return value
        for (doc, form), text in self.forms.items():
            a = text.find(value)
            if a >= 0:
                return {'$iu': [doc, a, a+len(value), form]}
        parts, end, changed = [], 0, False
        for match in re.finditer(r'\w+', value):
            if match.start() > end:
                parts.append(value[end:match.start()])
            token = match.group()
            replacement = token
            for (doc, form), text in self.forms.items():
                a = text.find(token)
                if a >= 0:
                    replacement = {'$iu': [doc, a, a+len(token), form]}
                    changed = True
                    break
            parts.append(replacement)
            end = match.end()
        if end < len(value):
            parts.append(value[end:])
        return {'$iu_join': parts} if changed else value

    def encode_embedded_surfaces(self, value):
        """Preserve JSON bytes while replacing short serialized text values."""
        parts, end, changed = [], 0, False
        pattern = r'"(?:text|surface|report_text)"\s*:\s*"((?:[^"\\]|\\.)*)"'
        for match in re.finditer(pattern, value):
            start, stop = match.span(1)
            replacement = self.encode_surface(match.group(1))
            if not isinstance(replacement, str):
                parts.extend([value[end:start], replacement])
                end = stop
                changed = True
        if not changed:
            return value
        parts.append(value[end:])
        return {'$iu_join': parts}

    @lru_cache(maxsize=100000)
    def encode_string(self, value):
        embedded = self.encode_embedded_surfaces(value)
        if not isinstance(embedded, str):
            # Process the surrounding literals as well, without altering bytes.
            return {'$iu_join': [self.encode_string(x) if isinstance(x, str) else x
                                 for x in embedded['$iu_join']]}
        if len(value) < 2:
            return value
        # Entire entity surfaces and short examples are also indirect references.
        if len(value) < 2000:
            for (doc, form), text in self.forms.items():
                a = text.find(value)
                if a >= 0:
                    return {'$iu': [doc, a, a+len(value), form]}
        tokens = list(re.finditer(r'\w+', value))
        spans = []
        end = 0
        for i in range(len(tokens)-2):
            a = tokens[i].start()
            if a < end:
                continue
            key = tuple(t.group() for t in tokens[i:i+3])
            best = None
            for doc, form, p in self.index.get(key, []):
                src = self.forms[doc, form]
                n = 0
                while p+n < len(src) and a+n < len(value) and src[p+n] == value[a+n]:
                    n += 1
                if a+n >= tokens[i+2].end() and (best is None or n > best[0]):
                    best = (n, doc, form, p)
            if best:
                n, doc, form, p = best
                spans.append((a, a+n, {'$iu': [doc, p, p+n, form]}))
                end = a+n
        if not spans:
            return value
        parts = []
        end = 0
        for a, b, ref in spans:
            if a > end:
                parts.append(value[end:a])
            parts.append(ref)
            end = b
        if end < len(value):
            parts.append(value[end:])
        return {'$iu_join': parts}

    def encode(self, value):
        if isinstance(value, str):
            return self.encode_string(value)
        if isinstance(value, list):
            return [self.encode(x) for x in value]
        if isinstance(value, dict):
            if '$iu' in value or '$iu_join' in value:
                raise ValueError('Reserved codec key in input')
            surface_keys = {'text', 'surface', 'report_text', 'span_text', 'source_text',
                            'document_text', 'sentence', 'quote', 'quoted_text', 'excerpt', 'context'}
            return {k: (self.encode_surface(v) if k.casefold() in surface_keys and isinstance(v, str)
                        else self.encode(v)) for k, v in value.items()}
        return value

    def decode(self, value):
        if isinstance(value, dict):
            if set(value) == {'$iu'}:
                doc, a, b, form = value['$iu']
                text = self.forms[str(doc), form]
                if not 0 <= a < b <= len(text):
                    raise ValueError('Invalid IU reference bounds')
                return text[a:b]
            if set(value) == {'$iu_join'}:
                return ''.join(self.decode(x) for x in value['$iu_join'])
            return {k: self.decode(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.decode(x) for x in value]
        return value


def verified_reports(path, reference_path):
    reports = [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    expected = {str(r['doc_id']): r for r in map(json.loads, reference_path.read_text(encoding='utf-8-sig').splitlines())}
    if len(reports) != len(expected) or len({str(r['doc_id']) for r in reports}) != len(reports):
        raise ValueError('Expected exactly the 50 unique study reports')
    for r in reports:
        ref = expected[str(r['doc_id'])]
        if hashlib.sha256(r['text'].encode()).hexdigest() != ref['text_sha256']:
            raise ValueError('Report hash mismatch: '+str(r['doc_id']))
    return reports
