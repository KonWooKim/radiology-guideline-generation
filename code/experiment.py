"""Portable entry points for the released historical annotation procedure.

No call is made without --execute. Use a NEW output directory, never an archived
run directory. Price snapshots are historical and are not current price quotes.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import types


def block_api_imports():
    module = types.ModuleType('openai')
    class Disabled:
        def __init__(self, *a, **kw):
            raise RuntimeError('API calls disabled. An explicit --execute is required')
    module.OpenAI = Disabled
    sys.modules['openai'] = module
    sys.modules.setdefault('psutil', types.ModuleType('psutil'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['develop', 'evaluate'])
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--provider', choices=['openai','deepseek'], required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--effort', choices=['high','max'], default='high')
    p.add_argument('--entity-guidelines', type=Path)
    p.add_argument('--relation-guidelines', type=Path)
    p.add_argument('--joint-guidelines', type=Path)
    p.add_argument('--minimal', action='store_true')
    p.add_argument('--fewshot', type=int, choices=[4,8,12])
    p.add_argument('--demo-plan', type=Path)
    p.add_argument('--entity-predictions', type=Path, help='Saved predictions for a fixed-entity relation condition')
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--max-retries', type=int)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    if a.max_retries is None:
        a.max_retries = 5 if a.action == 'develop' else 8
    w = a.workspace.resolve()
    out = a.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output must be new or empty. Do not overwrite a saved experiment')
    if w/'llm_preliminary/runs' in out.parents or out == w/'llm_preliminary/runs':
        raise ValueError('New experiments must not be written inside the archived runs')
    sys.path.insert(0, str(w/'scripts'))
    if not a.execute:
        block_api_imports()
    import run_two_phase_preliminary as two
    import run_heldout38 as held
    gold = w/'study_resources/emnlp_guideline_study/data/interim/iu_xray/human_gold_with_relations.jsonl'
    plan = w/'llm_preliminary/two_phase_experiment_plan.json'
    if a.action == 'develop':
        cond = next(c for c in json.loads(plan.read_text())['conditions'] if c['condition_id']=='C13_n12')
        rows = two.load_selected(gold, cond['doc_ids'])
        assert len(rows) == 12 and all(r['split'] == 'pilot' for r in rows)
        commands = [
            ['run_two_phase_preliminary.py','--gold',str(gold),'--plan',str(plan),'--condition','C13_n12',
             '--provider',a.provider,'--model',a.model,'--reasoning-effort',a.effort,
             '--output',str(out/'full12'),'--relation-mode','seed-only','--max-retries',str(a.max_retries)],
            ['run_relation_causal_preliminary.py','--gold',str(gold),'--plan',str(plan),
             '--source',str(out/'full12'),'--provider',a.provider,'--model',a.model,
             '--reasoning-effort',a.effort,'--output',str(out/'relation_causal'),'--max-retries',str(a.max_retries)]]
        print(json.dumps({'development_reports':12,'evaluation_gold_in_generation':False,
                          'commands':commands,'will_call_API':a.execute}, indent=2))
        if a.execute:
            import run_relation_causal_preliminary as causal
            sys.argv = commands[0]; two.main()
            sys.argv = commands[1]; causal.main()
        return
    rows = held.load_heldout(gold)
    fs = None
    if a.fewshot:
        if a.joint_guidelines or a.entity_predictions or a.minimal:
            raise ValueError('Few-shot is a separate two-stage condition')
        import run_deepseek_fewshot_budget as fs
        if not a.demo_plan:
            raise ValueError('Specify the archived demonstration-order plan explicitly')
        spec = json.loads(a.demo_plan.read_text(encoding='utf-8-sig'))['conditions']
        cid = f'FS{a.fewshot}_direct_gold'
        ids = [str(i) for i in spec[cid]['demonstration_doc_ids']]
        pilot = {str(r['doc_id']):r for r in fs.load_rows(gold) if r['split']=='pilot'}
        assert len(ids)==a.fewshot and set(ids)<=set(pilot)
        conditions = {cid:{'demo_ids':ids,'entity_guidance':'No additional annotation guideline is provided.',
                           'relation_guidance':'No additional annotation guideline is provided.',
                           'entity_demonstrations':[fs.entity_demonstration(pilot[i]) for i in ids],
                           'relation_demonstrations':[fs.relation_demonstration(pilot[i]) for i in ids]}}
    elif a.joint_guidelines:
        guidance = a.joint_guidelines.read_text(encoding='utf-8')
        if not guidance.strip():
            raise ValueError('Empty joint guidelines')
        conditions = {'requested':guidance}
    elif a.minimal:
        conditions = {'requested':('No additional operational guideline is provided.',)*2}
    else:
        if not a.entity_guidelines or not a.relation_guidelines:
            raise ValueError('Provide both phase inputs, --joint-guidelines, or --minimal')
        conditions = {'requested':(held.guideline_text(a.entity_guidelines, 'entity'),
                                   held.guideline_text(a.relation_guidelines, 'relation'))}
    if fs:
        payloads = [fs.entity_payload(r,conditions[cid]) for r in rows]
        assert all('entities' not in x['target_report'] and 'relations' not in x['target_report'] for x in payloads)
    elif not a.joint_guidelines:
        payloads = [held.entity_payload(r, conditions['requested'][0]) for r in rows]
        assert all('entities' not in x['report'] and 'relations' not in x['report'] for x in payloads)
    fixed = None
    if a.entity_predictions:
        fixed = json.loads(a.entity_predictions.read_text(encoding='utf-8-sig'))
        assert {str(r['doc_id']) for r in fixed}=={str(r['doc_id']) for r in rows} and len(fixed)==38
        gold_text = {str(r['doc_id']):r['text'] for r in rows}
        assert all(r['text']==gold_text[str(r['doc_id'])] for r in fixed)
    print(json.dumps({'evaluation_reports':38,'architecture':'joint' if a.joint_guidelines else ('fixed_entities' if fixed else 'two_stage'),
                      'expected_successful_calls':38 if a.joint_guidelines or fixed else 76,
                      'will_call_API':a.execute,'normalization_required_after_generation':True}))
    if not a.execute:
        return
    out.mkdir(parents=True, exist_ok=True)
    api = held.FrozenAPI(a.provider,a.model,a.effort,a.max_retries,False,out)
    # Costs require an up-to-date, separately supplied pricing policy. Save raw
    # usage and timings and do not report an old price snapshot as a current bill.
    held.token_cost = lambda provider, usage, at_utc=None: {
        'computed_usd':None,'qualification':'Price not estimated by portable runner. Apply current provider rates to saved usage.'}
    if fs:
        entities = fs.annotate_entities(api,conditions,rows,out,a.workers)
        fs.annotate_relations(api,conditions,rows,entities,out,a.workers)
    elif a.joint_guidelines:
        held.annotate_joint_all(api,conditions,rows,out,a.workers)
    elif fixed:
        held.annotate_relations_all(api,conditions,rows,{'requested':fixed},out,a.workers)
    else:
        entities = held.annotate_entities_all(api,conditions,rows,out,a.workers)
        held.annotate_relations_all(api,conditions,rows,entities,out,a.workers)


if __name__ == '__main__':
    main()
