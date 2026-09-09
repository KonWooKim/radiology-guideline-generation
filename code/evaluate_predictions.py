"""Evaluate text-free RadGraph-style prediction files.

The evaluator implements the manuscript's exact and overlap entity matching,
end-to-end relation scoring, and matched-endpoint relation diagnostic. With a
second prediction file it also computes report-level paired percentile
bootstrap contrasts. It needs offsets, labels, directed edges, and document
digests only; report text and entity surface strings are neither read nor
required.

Reference relation triples are de-duplicated independently of predictions.
The matched-endpoint metric is conditional on the endpoints produced in each
condition and is not an oracle rerun with reference entities.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path


ENTITY_LABELS = ("ANAT", "OBS-DP", "OBS-DA", "OBS-U")
RELATION_LABELS = ("Modify", "LocatedAt", "SuggestiveOf")
DEFAULT_BOOTSTRAP_SEED = 20260804
METRIC_KEYS = (
    "entity_exact",
    "entity_overlap",
    "relation_end_to_end_exact",
    "relation_end_to_end_overlap",
    "relation_matched_endpoint_exact",
    "relation_matched_endpoint_overlap",
)


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def entity_key(entity: dict) -> tuple[int, int, str]:
    return int(entity["start"]), int(entity["end"]), str(entity["label"])


def _overlap(first: dict, second: dict) -> int:
    return max(
        0,
        min(int(first["end"]), int(second["end"]))
        - max(int(first["start"]), int(second["start"])),
    )


def _iou(first: dict, second: dict) -> float:
    intersection = _overlap(first, second)
    if not intersection:
        return 0.0
    union = max(int(first["end"]), int(second["end"])) - min(
        int(first["start"]), int(second["start"])
    )
    return intersection / union


def entity_mapping(
    reference_entities: list[dict], prediction_entities: list[dict], mode: str
) -> dict[int, int]:
    """Return a maximum-cardinality labeled mapping: prediction index to gold.

    Exact matching requires equal half-open boundaries. Overlap matching
    requires positive character overlap. Candidate order uses IoU only as a
    deterministic preference inside maximum-cardinality bipartite matching.
    """
    if mode not in {"exact", "overlap"}:
        raise ValueError(f"Unknown entity matching mode: {mode}")
    adjacency: dict[int, list[int]] = {}
    for prediction_index, prediction in enumerate(prediction_entities):
        candidates = []
        for reference_index, reference in enumerate(reference_entities):
            if str(prediction["label"]) != str(reference["label"]):
                continue
            valid = (
                entity_key(prediction) == entity_key(reference)
                if mode == "exact"
                else _overlap(prediction, reference) > 0
            )
            if valid:
                candidates.append(reference_index)
        adjacency[prediction_index] = sorted(
            candidates,
            key=lambda index: (
                -_iou(prediction, reference_entities[index]),
                int(reference_entities[index]["start"]),
                index,
            ),
        )

    reference_to_prediction: dict[int, int] = {}

    def augment(prediction_index: int, seen: set[int]) -> bool:
        for reference_index in adjacency[prediction_index]:
            if reference_index in seen:
                continue
            seen.add(reference_index)
            if reference_index not in reference_to_prediction or augment(
                reference_to_prediction[reference_index], seen
            ):
                reference_to_prediction[reference_index] = prediction_index
                return True
        return False

    for prediction_index in sorted(
        adjacency,
        key=lambda index: (
            len(adjacency[index]),
            int(prediction_entities[index]["start"]),
            index,
        ),
    ):
        augment(prediction_index, set())
    return {
        prediction_index: reference_index
        for reference_index, prediction_index in reference_to_prediction.items()
    }


def _counter_counts(reference_items: list[tuple], prediction_items: list[tuple]) -> Counter:
    reference_counter = Counter(reference_items)
    prediction_counter = Counter(prediction_items)
    true_positive = sum((reference_counter & prediction_counter).values())
    return Counter(
        tp=true_positive,
        fp=sum(prediction_counter.values()) - true_positive,
        fn=sum(reference_counter.values()) - true_positive,
    )


def _reference_relation_items(record: dict) -> list[tuple[int, str, int]]:
    """Return prediction-independent unique reference triples by entity index."""
    index = {
        str(entity["id"]): position
        for position, entity in enumerate(record["entities"])
    }
    return sorted(
        {
            (
                index[str(relation["subj"])],
                str(relation["pred"]),
                index[str(relation["obj"])],
            )
            for relation in record["relations"]
        }
    )


def _relation_counts(
    reference: dict,
    prediction: dict,
    mapping: dict[int, int],
    conditional: bool,
) -> tuple[Counter, int, int]:
    """Return counts and endpoint-available/total reference relation counts."""
    prediction_index = {
        str(entity["id"]): position
        for position, entity in enumerate(prediction["entities"])
    }
    reference_items_all = _reference_relation_items(reference)
    mapped_reference = set(mapping.values())
    reference_items = [
        item
        for item in reference_items_all
        if not conditional or (item[0] in mapped_reference and item[2] in mapped_reference)
    ]

    prediction_items: list[tuple[int, str, int]] = []
    unmapped_predictions = 0
    for relation in prediction["relations"]:
        subject = prediction_index[str(relation["subj"])]
        object_ = prediction_index[str(relation["obj"])]
        if subject in mapping and object_ in mapping:
            prediction_items.append(
                (mapping[subject], str(relation["pred"]), mapping[object_])
            )
        elif not conditional:
            unmapped_predictions += 1
    result = _counter_counts(reference_items, prediction_items)
    result["fp"] += unmapped_predictions
    available = sum(
        subject in mapped_reference and object_ in mapped_reference
        for subject, _, object_ in reference_items_all
    )
    return result, available, len(reference_items_all)


def _validate_pair(reference: dict, prediction: dict) -> None:
    if str(reference["doc_id"]) != str(prediction["doc_id"]):
        raise ValueError("Reference and prediction document identifiers differ")
    if reference.get("text_sha256") != prediction.get("text_sha256"):
        raise ValueError(f"Document digest mismatch for {reference['doc_id']}")
    if reference.get("text_length") != prediction.get("text_length"):
        raise ValueError(f"Document length mismatch for {reference['doc_id']}")


def evaluate_document(reference: dict, prediction: dict) -> dict[str, Counter | int]:
    _validate_pair(reference, prediction)
    result: dict[str, Counter | int] = {}
    for mode in ("exact", "overlap"):
        mapping = entity_mapping(reference["entities"], prediction["entities"], mode)
        result[f"entity_{mode}"] = Counter(
            tp=len(mapping),
            fp=len(prediction["entities"]) - len(mapping),
            fn=len(reference["entities"]) - len(mapping),
        )
        end_to_end, available, total = _relation_counts(
            reference, prediction, mapping, conditional=False
        )
        matched_endpoint, _, _ = _relation_counts(
            reference, prediction, mapping, conditional=True
        )
        result[f"relation_end_to_end_{mode}"] = end_to_end
        result[f"relation_matched_endpoint_{mode}"] = matched_endpoint
        result[f"endpoint_available_{mode}"] = available
        result[f"endpoint_total_{mode}"] = total
    return result


def _aligned_documents(reference: list[dict], predictions: list[dict]) -> dict[str, dict]:
    prediction_by_id = {str(row["doc_id"]): row for row in predictions}
    reference_ids = {str(row["doc_id"]) for row in reference}
    if len(prediction_by_id) != len(predictions):
        raise ValueError("Duplicate prediction document identifier")
    if set(prediction_by_id) != reference_ids:
        raise ValueError("Reference and prediction document identifiers differ")
    return {
        str(row["doc_id"]): evaluate_document(
            row, prediction_by_id[str(row["doc_id"])]
        )
        for row in reference
    }


def score(count_values: Counter | dict) -> dict:
    values = Counter(count_values)
    true_positive = int(values["tp"])
    false_positive = int(values["fp"])
    false_negative = int(values["fn"])
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    denominator = 2 * true_positive + false_positive + false_negative
    f1 = 2 * true_positive / denominator if denominator else 0.0
    return {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def summarize(document_results: dict[str, dict]) -> dict:
    output = {
        metric: score(
            sum(
                (Counter(result[metric]) for result in document_results.values()),
                Counter(),
            )
        )
        for metric in METRIC_KEYS
    }
    for mode in ("exact", "overlap"):
        available = sum(
            int(result[f"endpoint_available_{mode}"])
            for result in document_results.values()
        )
        total = sum(
            int(result[f"endpoint_total_{mode}"])
            for result in document_results.values()
        )
        output[f"relation_endpoint_ceiling_{mode}"] = {
            "available_gold_relations": available,
            "total_gold_relations": total,
            "ceiling_recall": available / total if total else 0.0,
        }
    return output


def evaluate(reference: list[dict], predictions: list[dict]) -> dict:
    return summarize(_aligned_documents(reference, predictions))


def counts(reference: list[dict], predictions: list[dict], kind: str) -> dict:
    """Backward-compatible exact-score helper used by release validation."""
    metric = {
        "entity": "entity_exact",
        "relation": "relation_end_to_end_exact",
    }.get(kind)
    if metric is None:
        raise ValueError(kind)
    return evaluate(reference, predictions)[metric]


def percentile(values: list[float], proportion: float) -> float:
    if not values:
        raise ValueError("Cannot compute a percentile from no values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = math.floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_bootstrap(
    first_results: dict[str, dict],
    second_results: dict[str, dict],
    metric: str,
    replicates: int,
    seed: int,
) -> dict:
    """Compute first-minus-second micro-F1 by paired report bootstrap."""
    if metric not in METRIC_KEYS:
        raise ValueError(metric)
    document_ids = sorted(first_results)
    if document_ids != sorted(second_results):
        raise ValueError("Paired bootstrap document identifiers differ")

    def aggregate(results: dict[str, dict], sampled: list[str]) -> float:
        merged = sum(
            (Counter(results[doc_id][metric]) for doc_id in sampled), Counter()
        )
        return score(merged)["f1"]

    observed = aggregate(first_results, document_ids) - aggregate(
        second_results, document_ids
    )
    rng = random.Random(seed)
    differences = []
    for _ in range(replicates):
        sampled = [
            document_ids[rng.randrange(len(document_ids))]
            for _ in document_ids
        ]
        differences.append(
            aggregate(first_results, sampled)
            - aggregate(second_results, sampled)
        )
    return {
        "contrast": "predictions minus compare",
        "difference": observed,
        "ci95_lower": percentile(differences, 0.025),
        "ci95_upper": percentile(differences, 0.975),
        "replicates": replicates,
        "seed": seed,
        "unit": "report",
        "interval": "percentile 95%",
    }


def _select_reference(reference: list[dict], prediction_ids: set[str]) -> list[dict]:
    selected = [row for row in reference if str(row["doc_id"]) in prediction_ids]
    if {str(row["doc_id"]) for row in selected} != prediction_ids:
        raise ValueError(
            "Prediction file contains document identifiers absent from reference"
        )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exact/overlap and matched-endpoint evaluation without report text."
    )
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument(
        "--compare",
        type=Path,
        help="Optional second prediction file; contrasts are predictions minus compare.",
    )
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=0,
        help="Paired report-bootstrap replicates for every F1 contrast (0 disables).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_BOOTSTRAP_SEED,
        help="Bootstrap seed applied independently and unchanged to every metric.",
    )
    args = parser.parse_args()
    if args.bootstrap < 0:
        parser.error("--bootstrap must be nonnegative")

    reference_all = load_jsonl(args.reference)
    predictions = load_jsonl(args.predictions)
    prediction_ids = {str(row["doc_id"]) for row in predictions}
    reference = _select_reference(reference_all, prediction_ids)
    first_results = _aligned_documents(reference, predictions)
    result = {
        "reference": str(args.reference),
        "predictions": str(args.predictions),
        "documents": len(reference),
        "definitions": {
            "entity_exact": "one-to-one match requires identical half-open offsets and label",
            "entity_overlap": "maximum-cardinality one-to-one match requires positive character overlap and identical label",
            "relation_end_to_end": "directed predicate and both mapped endpoints must match; predictions with an unmapped endpoint are false positives",
            "relation_matched_endpoint": "conditional diagnostic restricted to relations whose endpoints enter that condition's entity mapping; not an oracle rerun",
            "reference_relation_deduplication": "exact duplicate directed reference triples are removed before every relation metric",
        },
        "scores": summarize(first_results),
    }
    if args.compare:
        comparison = load_jsonl(args.compare)
        if {str(row["doc_id"]) for row in comparison} != prediction_ids:
            raise ValueError(
                "Prediction and comparison document identifiers differ"
            )
        second_results = _aligned_documents(reference, comparison)
        result["compare"] = str(args.compare)
        result["compare_scores"] = summarize(second_results)
        result["contrasts"] = {}
        for metric in METRIC_KEYS:
            first_score = result["scores"][metric]["f1"]
            second_score = result["compare_scores"][metric]["f1"]
            contrast = {
                "contrast": "predictions minus compare",
                "difference": first_score - second_score,
            }
            if args.bootstrap:
                contrast = paired_bootstrap(
                    first_results,
                    second_results,
                    metric,
                    args.bootstrap,
                    args.seed,
                )
            result["contrasts"][metric] = contrast
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
