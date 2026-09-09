"""Independently validate the public package. Standard library only, no network."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import evaluate_predictions as ev

ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
    if not ok: raise ValueError(msg)
def countkeys(r,phase):
    es={e['id']:(e['start'],e['end'],e['label']) for e in r['entities']}
    if phase=='entity': return Counter(es.values())
    return Counter((es[e['subj']],e['pred'],es[e['obj']]) for e in r['relations'])
def development_score(ref,pred,phase):
    pb={r['doc_id']:r for r in pred}
    out=Counter()
    for g in ref:
        a,b=countkeys(g,phase),countkeys(pb[g['doc_id']],phase)
        out.update(tp=sum((a&b).values()),fp=sum((b-a).values()),fn=sum((a-b).values()))
    return ev.score(out)
def checkgraph(r):
    require('text' not in r,'Unexpected report text')
    ids={e['id'] for e in r['entities']}
    require(len(ids)==len(r['entities']),'Duplicate entity IDs')
    for e in r['entities']:
        require(set(e)=={'id','start','end','label'},'Unexpected entity field')
        require(e['label'] in ev.ENTITY_LABELS,'Unknown entity label')
        require(isinstance(e['start'],int) and isinstance(e['end'],int),'Noninteger offsets')
        require(0<=e['start']<e['end']<=r['text_length'],'Invalid span boundaries')
    for e in r.get('relations',[]):
        require(set(e)=={'id','subj','pred','obj'},'Unexpected relation field')
        require(e['subj'] in ids and e['obj'] in ids,'Unknown endpoint')
        require(e['pred'] in ev.RELATION_LABELS,'Unknown predicate')

def main():
    ref=rows(ROOT/'annotations/reference.jsonl'); rb={r['doc_id']:r for r in ref}
    require(len(ref)==len(rb)==50,'Reference coverage')
    dev=[r for r in ref if r['split']=='development']
    test=[r for r in ref if r['split']=='evaluation']
    require((len(dev),len(test))==(12,38),'Reference split')
    require(sum(len(r['entities']) for r in ref)==1988,'Reference entity count')
    require(sum(len(r['relations']) for r in ref)==1454,'Original relation count')
    require(sum(len(countkeys(r,'relation')) for r in ref)==1452,'Distinct relation count')
    for r in ref: checkgraph(r)
    registry=read(ROOT/'metadata/conditions.json'); metrics_checked=0
    for c in registry:
        pred=rows(ROOT/c['path'])
        for r in pred: checkgraph(r)
        require({r['doc_id'] for r in pred}=={r['doc_id'] for r in test},'Evaluation IDs')
        scores=ev.summarize(ev._aligned_documents(test,pred))
        for kind,wanted in (c.get('expected_exact_scores') or {}).items():
            key='entity_exact' if kind=='entity' else 'relation_end_to_end_exact'
            for k,v in wanted.items():
                require(abs(scores[key][k]-v)<1e-12,f"Score mismatch: {c['model']} {c['condition']} {kind} {k}")
            metrics_checked+=1
    total=accepted=0
    for p in sorted((ROOT/'development').glob('*_trials.jsonl.gz')):
        model,phase=p.name.split('_')[:2]
        phase=phase.split('.')[0]
        history=[json.loads(s) for s in gzip.decompress(p.read_bytes()).decode().splitlines()]
        current=development_score(dev,rows(ROOT/f'predictions/development/{model}/{phase}_initial.jsonl'),phase)
        for item in history:
            for r in item['predictions']: checkgraph(r)
            actual=development_score(dev,item['predictions'],phase)
            d=item['decision']
            for k in ('tp','fp','fn','f1'):
                require(abs(current[k]-d['before'][k])<1e-12,'Development before score')
                require(abs(actual[k]-d['after'][k])<1e-12,'Development candidate score')
            if d['accepted']:
                require(actual['f1']>current['f1']+1e-12,'Unexpected non-improving acceptance')
                current=actual; accepted+=1
            total+=1
    require((total,accepted)==(271,54),'Trial totals')
    checked_files=0
    manifest=ROOT/'MANIFEST.json'
    if manifest.exists():
        for r in read(manifest)['files']:
            require(sha(ROOT/r['path'])==r['sha256'],'Checksum mismatch: '+r['path'])
            checked_files+=1
    for p in ROOT.rglob('*'):
        if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts: continue
        raw=gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text(encoding='utf-8-sig')
        require(not re.search(r'(?:sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',raw),'Credential pattern')
        require(not re.search(r'C:[\\/]+Users[\\/]',raw,re.I),'Local user path')
    print(json.dumps(dict(status='PASS',reference_reports=50,evaluation_conditions=len(registry),
          exact_metric_rows_verified=metrics_checked,trials_verified=total,accepted_verified=accepted,
          checksum_files_verified=checked_files,api_calls=0),indent=2))

if __name__=='__main__': main()
