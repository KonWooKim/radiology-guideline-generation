"""Check original saved entity and few-shot request payloads after restoration."""
import argparse
import json
from pathlib import Path
import sys
from experiment import block_api_imports


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    a=p.parse_args(); w=a.workspace.resolve()
    block_api_imports();sys.path.insert(0,str(w/'scripts'))
    import run_heldout38 as held
    import run_deepseek_fewshot_budget as fs
    gold=fs.load_rows(w/'study_resources/emnlp_guideline_study/data/interim/iu_xray/human_gold_with_relations.jsonl')
    by={str(r['doc_id']):r for r in gold}
    checked=0
    runs=w/'llm_preliminary/runs'
    for run in ['deepseek_v4_pro_heldout38_final_v2','gpt_5_6_terra_high_heldout38_final_v2']:
        for path in (runs/run).glob('*/entity_prompts/*.json'):
            saved=read(path)['user']
            actual=held.entity_payload(by[path.stem],saved['operational_guidance'])
            assert actual==saved,path
            checked+=1
    for run in ['deepseek_v4_pro_high_fewshot_4_8_12_20260828_run01','gpt_5_6_sol_high_fewshot_4_8_12_20260829_run01']:
        for path in (runs/run).glob('FS*/entity_prompts/*.json'):
            saved=read(path)['user']; demos=saved['demonstrations']
            ids=[x['report']['doc_id'] for x in demos]
            c={'entity_guidance':saved['operational_guidance'],
               'entity_demonstrations':[fs.entity_demonstration(by[str(i)]) for i in ids]}
            assert fs.entity_payload(by[path.stem],c)==saved,path
            assert set(ids)<=set(str(r['doc_id']) for r in gold if r['split']=='pilot')
            checked+=1
        for path in (runs/run).glob('FS*/relation_prompts/*.json'):
            saved=read(path)['user'];ids=[x['report']['doc_id'] for x in saved['demonstrations']]
            c={'relation_guidance':saved['operational_guidance'],
               'relation_demonstrations':[fs.relation_demonstration(by[str(i)]) for i in ids]}
            assert fs.relation_payload(by[path.stem],saved['immutable_entities'],c)==saved,path
            checked+=1
    assert checked>0
    print(json.dumps({'request_payloads_verified':checked,'API_calls':0,'status':'PASS'}))


if __name__=='__main__':main()
