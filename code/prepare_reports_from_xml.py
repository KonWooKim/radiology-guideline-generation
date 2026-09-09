"""Render user-obtained IU X-Ray XML and verify the released whole-report hashes.

No download and no annotation-label-dependent processing. Output is written only
if all 50 requested reports match. Keep XML and reconstructed text private/local.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from rehydrate_annotations import atomic_write

def clean(element):
    return ' '.join(''.join(element.itertext()).split()) if element is not None else ''

def render(path):
    root=ET.parse(path).getroot()
    sections={e.get('Label','').upper():clean(e) for e in root.findall('.//AbstractText')}
    caption=root.find('.//parentImage/caption')
    sections['IMAGE']=clean(caption)
    return '\n'.join(label+':\n'+sections[label] for label in
                     ('IMAGE','INDICATION','COMPARISON','FINDINGS','IMPRESSION') if sections.get(label))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--annotations',type=Path,required=True)
    p.add_argument('--xml-dir',type=Path,required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    annotations=[json.loads(s) for s in a.annotations.read_text(encoding='utf-8').splitlines() if s.strip()]
    output=[]; mismatches=[]
    for r in annotations:
        path=a.xml_dir/(str(r['doc_id'])+'.xml')
        text=render(path)
        if hashlib.sha256(text.encode()).hexdigest()!=r['text_sha256']:
            mismatches.append(dict(doc_id=r['doc_id'],expected_length=r['text_length'],actual_length=len(text)))
        else: output.append(dict(doc_id=r['doc_id'],text=text))
    if mismatches:
        print(json.dumps(dict(status='MISMATCH',verified=len(output),mismatches=mismatches),indent=2))
        raise SystemExit(1)
    if a.output: atomic_write(a.output,output)
    print(json.dumps(dict(status='PASS',reports=len(output),output_written=bool(a.output)),indent=2))

if __name__=='__main__': main()
