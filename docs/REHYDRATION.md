# Reconstructing the report text

The public annotation layer uses offsets into the complete normalized report,
not offsets relative to Findings or Impression alone. The reference annotations
are limited to Findings/Impression, but other report sections remain part of the
offset coordinate system.

Obtain the source XML reports independently from Open-i. The preparation utility
expects filenames such as `{doc_id}.xml` inside the directory supplied through
`--xml-dir`. Run `code/prepare_reports_from_xml.py` before the rehydration utility,
as shown in the README. XML files and generated report text stay outside GitHub.

The verified rendering uses the first image caption as IMAGE, followed by
INDICATION, COMPARISON, FINDINGS, and IMPRESSION in that order. Empty sections are
omitted. Each heading is uppercase followed by a colon and a newline. XML text
whitespace is collapsed to single spaces, sections are separated by one newline,
and no newline is appended to the complete report. MeSH and Problems metadata are
not included in the offset-bearing report text. This procedure matched all 50
released whole-report hashes using the locally available original XML files.

The exact source representation matters. Do not silently trim or change text
until its complete SHA-256 and character length match the public record.
Line endings, headings, spaces, punctuation, and section ordering can all change
offsets. The hash is calculated on the UTF-8 bytes of the complete normalized
string. Offsets count Python Unicode characters, not UTF-8 bytes.

This release does not include an automated remote downloader. If your
download uses a different text rendering, the validator deliberately stops
instead of placing annotations at unverified positions.

After a successful reconstruction, each entity surface can be obtained as
`text[start:end]`. The end position is excluded. Original duplicate reference
relation records are preserved in the annotation file, while the evaluator
deduplicates exact directed triples for scoring.
