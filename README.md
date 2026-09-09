# Radiology guideline generation

Expert annotations and evaluation materials for *Generating Annotation Guidelines
from 12 Annotated Radiology Reports: An Empirical Study and a 50-Report IU X-Ray
Annotation Resource*.

This repository supports evaluation of draft annotation guidelines generated from
a small annotated set when a directly applicable annotation manual is not supplied.
It is a research resource, not a clinical system or an independently adjudicated
annotation standard.

## Study at a glance

| Item | Scope |
|---|---|
| Reports | 50 IU X-Ray radiology reports |
| Development / evaluation | 12 first-round / 38 second-round reports |
| Human reference | One experienced biomedical corpus annotator |
| Reference entities | 1,988 total, 1,586 in evaluation |
| Reference relations | 1,454 source records, 1,452 distinct triples for scoring |
| Evaluation relations | 1,167 distinct directed triples |
| Main models | DeepSeek V4 Pro high, GPT-5.6 Terra high, GPT-5.6 Sol high |
| Secondary setting | DeepSeek V4 Pro max |
| Main development history | 271 candidate trials, 54 accepted revisions |

Human annotation followed this sequence: first round, Human v1, discussion,
second round, Human v2. The same expert annotated both rounds and wrote both
documents. The first-round annotations were not revised after discussion.
The author-provided initial RadGraph manual was obtained later and was not used
by the expert during either round.

## Contents

- `annotations/reference.jsonl`: all 50 reference graphs, report IDs, whole-report
  SHA-256 digests, and lengths. Original duplicate relation records are retained.
- `predictions/evaluation/`: normalized prediction graphs, with each execution
  identified in `metadata/conditions.json`. Original core results are kept
  separate from few-shot rerun controls and secondary experiments.
- `predictions/development/`: initial and refined entity/relation predictions
  on the 12 development reports, with the original selection-time offsets.
- `guidelines/`: report-text-redacted initial and refined guidelines for each
  main model, plus summaries of Human v1 and v2.
- `development/*_trials.jsonl.gz`: all 271 candidate decisions, redacted rules,
  and complete candidate predictions. Standard gzip-compressed JSON Lines.
- `prompts/`: report-independent templates. These are not verbatim API requests.
- `analysis/`: saved numerical comparisons, label scores, endpoint diagnostics,
  few-shot results, acceptance audits, and five-system pairwise agreement.
- `code/`: standard-library evaluation, rehydration, and validation utilities.
- `metadata/`: condition definitions, source hashes, and study scope.
- `MANIFEST.json` and `SHA256SUMS`: checksums for the published files.

## Quick start

Python 3.10 or newer is sufficient. No model API credentials or paid requests
are needed to evaluate these saved predictions.

```bash
python code/verify_release.py
python code/evaluate_predictions.py --reference annotations/reference.jsonl --predictions predictions/evaluation/Sol/Gstar.jsonl
```

Exact entity matching requires the same label and zero-based half-open character
offsets `[start, end)`. Overlap matching requires the same label and positive span
overlap with one-to-one maximum-cardinality matching. An end-to-end relation match
requires its directed label and both mapped endpoints to match. The evaluator
deduplicates exact reference relation triples without consulting predictions.

To compare two conditions with a paired report bootstrap:

```bash
python code/evaluate_predictions.py --reference annotations/reference.jsonl --predictions predictions/evaluation/Sol/Gstar.jsonl --compare predictions/evaluation/Sol/S0.jsonl --bootstrap 10000 --seed 20260828
```

The contrast is the first prediction file minus the comparison file. Saved
intervals retain their recorded analysis seeds and execution choices. A bootstrap
run with a different seed or report order need not give identical interval bounds.
Intervals quantify report-resampling uncertainty for fixed outputs, not LLM
run-to-run variability. They are unadjusted for multiple comparisons.

## Rehydrate the reports

Report text and images are not redistributed. Obtain the IU X-Ray corpus
independently from [Open-i](https://openi.nlm.nih.gov/). See
[`docs/REHYDRATION.md`](docs/REHYDRATION.md) for the required text representation.

From the original XML files, create the verified text representation and then
attach the annotations:

```bash
python code/prepare_reports_from_xml.py --annotations annotations/reference.jsonl --xml-dir /path/to/ecgen-radiology --output /path/to/reports.jsonl
python code/rehydrate_annotations.py --annotations annotations/reference.jsonl --reports /path/to/reports.jsonl --output /path/to/rehydrated_annotations.jsonl
```

Both utilities refuse mismatched whole-report hashes. XML-to-text reconstruction
and annotation rehydration were checked against all 50 reports and 1,988 annotated
spans. This verifies the local source representation, not continued availability
of the external download.
Keep rehydrated data outside this repository.

## Interpreting the conditions

- `S0`: shared minimal natural-language task instructions. It is not a prompt
  with only symbolic schema labels.
- `G0`: initial entity guidelines E0 and initial relation guidelines R0. R0 was
  generated after entity refinement with final predicted entities, so G0 is not
  a complete no-refinement pipeline.
- `Gstar`: refined entity and relation guidelines, E* and R*.
- `human`: Human v1, with phase-appropriate sections in two-stage annotation.
- `author`: the original authors' initial manual converted from Word, including
  its illustrated examples, with phase-appropriate inputs. The manual itself
  is not included here.
- `joint`: G* with entity and relation prediction in one request.
- `author_routed_joint`: concatenation of the unchanged two-stage Author inputs.
- `author_full` / `author_full_joint`: the full Author document in each stage
  or once in joint prediction. `human_joint` uses the full Human v1 document.
- `minimal_R`: final predicted entities with minimal relation instructions.
- `FS4`, `FS8`, `FS12`: direct demonstrations from one fixed nested ordering.
  `FSblock_*` are accompanying rerun controls, not replacements for core outputs.

See `metadata/conditions.json` for the complete file inventory. Withdrawn
text-only Author results and invalid empty-G0 results are excluded.

## Reuse and limitations

The resource permits rescoring saved outputs, benchmarking other annotation
instructions on the same reference, and inspecting saved guideline changes.
The development archives preserve selection-time numeric offsets. Later
evaluation normalization must not be retroactively treated as the procedure used
to select development revisions.

Report-bearing examples and supporting report identifiers were removed from
public guidelines. Embedded quotations and detected report fragments were also
redacted. These files support rule inspection but do not reproduce the exact
inference prompts or enable exact replay of guideline generation. Human guideline
summaries are editorial descriptions, not the actual Human v1 prompt.

Single-expert agreement is not clinical correctness or human consensus. Shared
AI predictions do not adjudicate disputed annotations. The two annotation rounds
were not randomly assigned and may reflect different conventions after discussion.
The main models span two model families. Provider-defined high reasoning settings
do not match compute budgets. DeepSeek max developed separate guidelines, so its
comparison is not an effort-only intervention with fixed instructions.

## Exclusions and licenses

IU report text/images, raw model responses and reasoning, report-bearing prompts,
the original Author manual, model checkpoints, and credentials are excluded.
See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Author-created annotation layers and documentation use CC BY 4.0
(`LICENSE-DATA`). Code uses MIT (`LICENSE-CODE`). Model outputs are included to
the extent the contributors hold rights, subject to the original provider terms.
No license here grants rights in excluded third-party materials.

Repository: <https://github.com/KonWooKim/radiology-guideline-generation>.
Until final manuscript bibliographic details are available, identify this
repository, the accessed commit, and the manuscript title when referencing the
resource. No archival DOI is claimed.
