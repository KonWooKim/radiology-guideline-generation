# Reproducing the study

## Three different operations

1. **Rescore fixed predictions:** no IU text or API is needed. Run `code/verify_release.py` and `code/evaluate_predictions.py`.
2. **Restore and replay the recorded procedure:** obtain the 50 source IU XML files independently, reconstruct the hash-checked reports, then restore the bundles. This requires no model API. It verifies the recorded selection and scoring, not a second independent model execution.
3. **Run a new experiment:** use the released procedure with your own model access and credentials. New generations need not be identical. Availability of the historical model versions is external to this repository.

The original Author manual, its Markdown conversions, its request bodies, and analysis indexes that reproduce its passages are excluded. Saved Author-condition predictions and their numerical analyses are included. Rerunning that condition requires independently obtaining the manual. The repository does not substitute the withdrawn text-only document.

## 1. Prepare a private workspace

Use Python 3.10 or later for the standard-library utilities. Analysis dependency versions used in release QA are listed separately from API dependencies. Historical run manifests retain the environment details that were recorded at execution time.

Run these commands from the public repository. Replace `/private/...` with your own paths. Keep reconstructed text outside the public checkout.

```bash
python code/prepare_reports_from_xml.py --annotations annotations/reference.jsonl --xml-dir /private/IU_XML --output /private/reports.jsonl
python code/restore_study.py --reports /private/reports.jsonl --output /private/study
python code/verify_selection_replay.py --workspace /private/study
python code/verify_prompt_parity.py --workspace /private/study
```

The restorer refuses a nonempty destination and a destination inside the public repository. Before writing, it checks the archive checksums, complete record index, and portable destination paths. Missing or duplicate records are rejected. It also verifies every report hash and every reconstructed artifact digest. Never commit `/private/study`.

## 2. What is restored

`reproduction/index.jsonl` identifies every artifact, its file, its original source hash and its restored hash. The index and reconstruction files are uncompressed UTF-8 JSON Lines for direct inspection. Each line is one complete record. Records contain literals and references to separately obtained IU text, not embedded report text. Each `$iu` reference specifies report ID, start, end and representation. `plain` uses the canonical report. `json` and `ascii` use JSON-escaped representations for exact reconstruction of nested request strings. Offsets refer to the specified representation and are not annotation spans.

`lower` and `upper` representations preserve case differences in legacy checkpoint text. These reference offsets are never used for scoring.

`indexed`, `indexed_json`, and `indexed_ascii` reconstruct the deterministic
`[start:end]word` offset aid from a separately obtained report, including its
JSON-escaped variants. The source words in this aid are not stored literally.

Entity surface strings inside JSON-serialized model answers also use text references. The surrounding JSON formatting is retained, so restoring an answer reproduces its exact recorded bytes rather than reserializing a parsed object. The readable [archive catalog](../reproduction/CONTENTS.md) lists each bundle's sources and record count.

The reconstruction includes:

- the full reference graphs and the fixed 12/38 split;
- Human v1 and v2, the actual cleaned Human v1 input, and frozen phase-routed inputs;
- initial and final generated guidelines, all rule fields, examples, exceptions, supporting IDs and candidate proposals;
- saved development predictions and all candidate decisions, including rejected trials;
- saved final-answer model responses, parsed outputs, normalized outputs and validation records;
- stored non-Author request payloads, prompt-building code, execution plans, schemas and provider settings;
- available usage, cost snapshots, timing, retry and execution metadata;
- analysis code and inputs, numerical tables and figure-generating code;
- checkpoint outputs and the reference-entity diagnostic inputs and results.

Provider hidden reasoning and credentials are not included. Their removal does not remove reported reasoning-token counts. JSON formatting is preserved where recognized. Path metadata is relocated from the original study directory. A source hash therefore need not equal the restored hash for a sanitized or relocated record. The actual Human v1 inference input is `study_resources/emnlp_guideline_study/data/human_guidelines/source_v1_round1.md`, not the legacy-encoded original file. Original expert files are retained for provenance with a lossless Latin-1-to-UTF-8 transcode where needed.

Historical names such as `secondary`, `gold`, `operational`, and `inventory` remain in executable artifacts because renaming request fields or instructions would change the recorded procedure. The current paper and `metadata/conditions.json` define the reporting terminology and canonical comparison scope.

One unrelated external-corpus example filename in the original Human v2 document is replaced by a neutral placeholder in the public representation. This documentary edit does not change an experimental input. The original source hash and the edited restoration hash are retained separately.

Superseded status notes, unused plans, manuscript drafts and manuscript backups are omitted. Actual requests, final-answer responses, candidate decisions and resource records are retained. Forty numerical rows needed from six historical table snapshots are provided as `analysis_inputs/compact_supplement_rows.json`. The released table builder reads these rows directly and verifies the output hash without requiring the original documents. `metadata/reproduction_retention.json` summarizes this boundary. The original experimental payloads are unchanged.

## 3. Replay analyses

The launcher disables model-client construction. Analyses write derived files inside the private restored workspace, not in the public checkout or original study archive. Run core mechanisms before agreement because it refreshes the source index for the restored files.

```bash
python code/offline_analysis.py --workspace /private/study --script analyze_three_model_mechanisms_20260906.py
python code/offline_analysis.py --workspace /private/study --script extend_cross_system_agreement_20260907.py
python code/offline_analysis.py --workspace /private/study --script audit_three_model_acceptance_20260908.py
python code/offline_analysis.py --workspace /private/study --script analyze_author_routed_joint_20260907.py
python code/offline_analysis.py --workspace /private/study --script build_compact_supplement_20260910.py --check
```

The mechanism analysis skips the excluded Author quotation lookup. All numerical analyses still use saved Author predictions. The compact supplement command validates table construction from saved evidence. It is not, by itself, a fresh bootstrap of every underlying contrast.

Few-shot normalization and contrasts can be recomputed from the saved responses:

```bash
python code/offline_analysis.py --workspace /private/study --script analyze_deepseek_fewshot_budget.py --run /private/study/llm_preliminary/runs/deepseek_v4_pro_high_fewshot_4_8_12_20260828_run01
python code/offline_analysis.py --workspace /private/study --script analyze_sol_fewshot_budget.py --run /private/study/llm_preliminary/runs/gpt_5_6_sol_high_fewshot_4_8_12_20260829_run01
```

Do not run every historical script indiscriminately. Some preserve withdrawn comparisons or require the excluded manual. Use the coverage table below. Bootstrap implementations and seeds are retained with their source analyses. They are not interchangeable with an arbitrary bootstrap command.

## 4. Run a new guideline-development experiment

First install `requirements-api.txt` and set `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` in your own environment. No credential is included here. Check your institution's data policy and current provider terms before transmitting your separately obtained reports.

This command is a dry run. It checks the development set and prints the two sequential commands:

```bash
python code/experiment.py develop --workspace /private/study --output /private/new_deepseek --provider deepseek --model deepseek-v4-pro --effort high
```

Add `--execute` only when you intend to incur API charges. The first stage generates E0, refines entity guidelines, fixes the final entity predictions, and generates R0. The second stage applies causal discrepancy selection to relation refinement. Every candidate is reannotated on all 12 reports. No evaluation annotation is included in generation inputs. There is no retrospective normalization of development outputs before admission.

Use `--provider openai --model gpt-5.6-terra`, `--model gpt-5.6-sol`, or DeepSeek `--effort max` to configure the corresponding procedure, subject to provider availability. Provider-defined efforts are not compute-matched. The same effort value does not guarantee the same token budget.

## 5. Evaluate guidelines and demonstrations

For E*/R*, provide the two generated files. For Human inputs, use the restored phase-routed files. For a joint comparison, provide the exact combined input with `--joint-guidelines`. For minimal instructions, use `--minimal`.

```bash
python code/experiment.py evaluate --workspace /private/study --output /private/new_eval --provider deepseek --model deepseek-v4-pro --entity-guidelines /private/new_deepseek/full12/entity/G_star/guideline.json --relation-guidelines /private/new_deepseek/relation_causal/R_star/guideline.json
```

Two-stage evaluation makes 38 entity and 38 relation requests. Joint evaluation makes 38 requests. A fixed-entity relation comparison accepts `--entity-predictions` and makes 38 relation requests. The latter file must be model predictions, not the reference entities, unless explicitly conducting a reference-entity diagnostic.

The following is a dry run for the original nested FS12 demonstration order:

```bash
python code/experiment.py evaluate --workspace /private/study --output /private/new_fs12 --provider deepseek --model deepseek-v4-pro --fewshot 12 --demo-plan /private/study/llm_preliminary/deepseek_high_fewshot_4_8_12_plan.json
```

Choose 4, 8 or 12 and the matching model's archived plan. The entity request contains entity demonstrations. The relation request contains relation demonstrations. Target reference annotations are never part of either request. The separate joint-FS12 runner is retained among historical sources.

All these commands require `--execute` for real requests. Start a fresh output directory. Do not reuse historical response caches as if they were independent new executions. The portable evaluator retains request bodies and raw responses. Its cost field is deliberately unset until current prices are applied to the usage ledger. Development runners retain their historical pricing implementation, so those estimates must also be recalculated at current rates.

Apply the same reference-blind normalization before comparing new evaluation results:

```bash
python code/normalize_output.py --workspace /private/study --condition-dir /private/new_eval/requested --output /private/new_eval_normalized
```

Raw output is never overwritten. Relation-only conditions need the raw entity responses from the run that produced their fixed entities if normalization has not already been applied.

## Coverage and boundaries

| Evidence | Reproduction route | Boundary |
|---|---|---|
| Exact and overlap scores, conditional relation scores | Public evaluator and saved graphs | No API or IU text needed |
| Discrepancy ranking, all evidence, ADD/REVISE, admission, final states | `verify_selection_replay.py` | Replays saved candidates, not stochastic generation |
| Entity and few-shot request payloads | `verify_prompt_parity.py` | Tests retained payloads, not provider-internal processing |
| Three-model label, endpoint, normality, common-error analyses and contrasts | `analyze_three_model_mechanisms_20260906.py` | Author textual quotations excluded |
| Five-system agreement and its bootstrap intervals | `extend_cross_system_agreement_20260907.py` | Uses fixed outputs from one reference annotator |
| Few-shot normalization, contrasts, resource totals | The two few-shot analyzers | Single nested demonstration order |
| Sol Author routed-joint completion | `analyze_author_routed_joint_20260907.py` | Rescores outputs without redistributing its input manual |
| Compact supplement | `build_compact_supplement_20260910.py --check` | Some historical resource/interval rows are retained source values |
| Figures and typeset tables | Restored generators and numerical inputs | Original manuscript drafts excluded. Optional rendering libraries/fonts required, not identical PDF bytes |
| Fresh LLM execution | `experiment.py` and historical runners | Own API access, available models, current terms and charges |
| Checkpoint inference | Saved outputs, alignment code, reference-entity diagnostic artifacts | Obtain checkpoint and its legacy runtime separately |

The 50 original checkpoint PubAnnotation outputs are reconstructable, so their
alignment can also be rerun without model inference:

```bash
python code/rebuild_checkpoint_input_zip.py --workspace /private/study
python code/offline_analysis.py --workspace /private/study --script build_aligned_radgraph_relations.py
```

The reconstructed ZIP contains only the 50 study records, not the complete
upstream IU output archive. A reference-entity diagnostic patch and upstream
license context are in `checkpoint_source/`. Apply that patch only to the
matching separately obtained DyGIE++ source. The saved diagnostic and exact-
boundary/released-tokenizer inputs are under `study_resources/emnlp_guideline_study/oracle/`.
They are a diagnostic intervention, not an independently adjudicated gold standard.

Release tests do not claim that every historical helper can be run in an arbitrary environment without external prerequisites. See `metadata/reproduction_validation.json` for the specific completed checks. In particular, exact historical costs cannot be recovered for attempts whose provider usage was never recorded, and current cloud services cannot guarantee byte-identical future generations.
