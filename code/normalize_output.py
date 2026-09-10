"""Apply the study's reference-blind offset processing to a new saved output."""
import argparse
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--condition-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError('Use a new output directory. Raw files must remain unchanged')
    sys.path.insert(0,str(a.workspace.resolve()/'scripts'))
    from reconcile_manuscript_comparators_20260905 import normalize
    predictions,audit=normalize(a.condition_dir.resolve())
    a.output.mkdir(parents=True,exist_ok=True)
    for name,value in [('predictions.json',predictions),('normalization_audit.json',audit)]:
        (a.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'documents':len(predictions),'examined_mismatches':len(audit),
                      'repaired':sum(r['status']=='repaired' for r in audit),'API_calls':0}))


if __name__=='__main__':main()
