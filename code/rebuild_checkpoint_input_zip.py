"""Reassemble the 50 saved checkpoint outputs after private IU restoration."""
import argparse
import json
from pathlib import Path
import zipfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    a=p.parse_args(); w=a.workspace.resolve()
    records=json.loads((w/'checkpoint_source/selected_pubannotation.json').read_text(encoding='utf-8'))
    out=w/'original resources/outputs_radgraph_on_IU.zip'
    if out.exists():raise ValueError('Refusing to overwrite an existing archive')
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,value in records.items():
            z.writestr(name,json.dumps(value,ensure_ascii=False))
    print(json.dumps({'checkpoint_records':len(records),'API_calls':0}))


if __name__=='__main__':main()
