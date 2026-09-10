"""Replay selection, proposal application and admission for the 271 saved trials.

No model inference. Stored candidate predictions are replayed, not regenerated.
"""
import argparse
import copy
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from experiment import block_api_imports


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    a = p.parse_args()
    block_api_imports()
    w = a.workspace.resolve()
    sys.path.insert(0,str(w/'scripts'))
    import run_two_phase_preliminary as two
    import run_relation_causal_preliminary as rel
    from audit_three_model_acceptance_20260908 import RUNS
    plan = read(w/'llm_preliminary/two_phase_experiment_plan.json')
    ids = next(c['doc_ids'] for c in plan['conditions'] if c['condition_id']=='C13_n12')
    gold = two.load_selected(w/'study_resources/emnlp_guideline_study/data/interim/iu_xray/human_gold_with_relations.jsonl',ids)
    counts = defaultdict(int)
    for model, phase, run in RUNS:
        folder = w/'llm_preliminary/runs'/run
        initial = folder/('G0' if phase=='entity' else 'R0')
        if (initial/'guideline.json').exists():
            guideline = read(initial/'guideline.json')
        else:
            guideline = two.validate_guideline(json.loads(read(folder/'entity_initial_raw.json')['choices'][0]['message']['content']), phase)
        pred = read(initial/'predictions.json')
        census_fn = two.entity_census if phase=='entity' else rel.causal_census
        score_fn = two.entity_score if phase=='entity' else two.relation_score
        rejected = defaultdict(set)
        for decision in read(folder/'state.json')['history']:
            i = decision['iteration']; cdir = folder/f'candidate_{i:03d}'
            census = {k:v for k,v in census_fn(gold,pred).items() if not k.startswith('UNAVAILABLE|')}
            sig = hashlib.sha256(json.dumps({'g':guideline['principles'],'c':census},sort_keys=True,default=str).encode()).hexdigest()
            ranked = [k for k,v in sorted(census.items(),key=lambda z:(-len(z[1]),-len({str(x['doc_id']) for x in z[1]}),z[0])) if k not in rejected[sig]]
            assert ranked and ranked[0]==decision['stratum'], (model,phase,i,'selection')
            prompt = read(cdir/'prompt.json')
            key = 'complete_discrepancy_evidence' if phase=='entity' else 'complete_causal_error_evidence'
            assert prompt[key]==census[ranked[0]], (model,phase,i,'evidence')
            assert prompt['current_principles']==guideline['principles'], (model,phase,i,'current_rules')
            if phase=='relation':
                assert prompt['complete_verified_true_positive_contrasts']==rel.true_positive_contrasts(ranked[0],gold,pred), (model,phase,i,'positive_contrasts')
            proposal = json.loads(read(cdir/'raw.json')['choices'][0]['message']['content'])
            proposed = two.apply_candidate(guideline,proposal,i,census[ranked[0]],phase)
            assert proposed==read(cdir/'guideline.json'), (model,phase,i,'apply')
            newpred = read(cdir/'predictions.json')
            assert len(newpred)==12 and {d['doc_id'] for d in newpred}=={d['doc_id'] for d in gold}
            before, after = score_fn(gold,pred), score_fn(gold,newpred)
            newc = census_fn(gold,newpred)
            accepted = after['f1']>before['f1']+1e-12 or (abs(after['f1']-before['f1'])<=1e-12 and sum(len(v) for k,v in newc.items() if not k.startswith('UNAVAILABLE|'))<sum(map(len,census.values())))
            assert accepted==decision['accepted'], (model,phase,i,'admission')
            counts['trials']+=1
            counts['accepted']+=accepted
            if accepted:
                guideline,pred=proposed,newpred
            else:
                rejected[sig].add(ranked[0])
        final = folder/('G_star' if phase=='entity' else 'R_star')
        assert guideline==read(final/'guideline.json') and pred==read(final/'predictions.json')
        census = {k:v for k,v in census_fn(gold,pred).items() if not k.startswith('UNAVAILABLE|')}
        sig = hashlib.sha256(json.dumps({'g':guideline['principles'],'c':census},sort_keys=True,default=str).encode()).hexdigest()
        assert not (set(census)-rejected[sig]), (model,phase,'untried categories remain at stopping')
        counts['exhausted_searches']+=1
    assert counts['trials']==271 and counts['accepted']==54
    assert counts['exhausted_searches']==6
    print(json.dumps(dict(counts)|{'selection_evidence_apply_admission':'PASS','API_calls':0},indent=2))


if __name__=='__main__':
    main()
