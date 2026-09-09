"""Verify independently obtained report text and attach released annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


def load(path: Path) -> dict[str, dict]:
    records = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        doc_id = str(record.get("doc_id", ""))
        if not doc_id:
            raise ValueError(f"{path}:{line_number} has no doc_id")
        if doc_id in records:
            raise ValueError(f"Duplicate doc_id {doc_id} in {path}")
        records[doc_id] = record
    return records


def atomic_write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def mismatch_hint(text: str, expected_length: int) -> str:
    hints = []
    if "\r\n" in text:
        hints.append("convert CRLF line endings to LF")
    elif "\r" in text:
        hints.append("convert CR line endings to LF")
    if text != text.strip():
        hints.append("remove leading or trailing whitespace")
    delta = len(text) - expected_length
    if delta:
        hints.append(f"length differs by {delta:+d} characters")
    return "; ".join(hints) or "content differs from the annotated normalized report"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True, help="JSONL with doc_id and exact normalized text")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    annotations, reports = load(args.annotations), load(args.reports)
    missing = sorted(set(annotations) - set(reports))
    if missing:
        raise ValueError(f"Missing source reports: {missing}")

    mismatches = []
    for doc_id, annotation in annotations.items():
        text = reports[doc_id]["text"]
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != annotation["text_sha256"]:
            mismatches.append((doc_id, mismatch_hint(text, int(annotation["text_length"]))))
    if mismatches:
        print("ERROR: report digests differ; no output was replaced.", file=sys.stderr)
        for doc_id, hint in mismatches[:10]:
            print(f"  {doc_id}: {hint}", file=sys.stderr)
        raise SystemExit(1)

    output = []
    for doc_id, annotation in annotations.items():
        text = reports[doc_id]["text"]
        entities = []
        for entity in annotation["entities"]:
            start, end = int(entity["start"]), int(entity["end"])
            if not 0 <= start < end <= len(text):
                raise ValueError(f"Invalid offset in {doc_id}: {entity}")
            entities.append({**entity, "text": text[start:end]})
        output.append({**annotation, "text": text, "entities": entities})
    atomic_write(args.output, output)
    print(f"Verified and rehydrated {len(output)} records to {args.output}")


if __name__ == "__main__":
    main()
