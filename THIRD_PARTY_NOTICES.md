# Third-party materials and exclusions

This package intentionally excludes the following third-party materials:

1. IU X-Ray/Open-i report text and images. Users must obtain them from their
   original distributor and comply with its terms. This release provides only
   author-created annotations, document identifiers, lengths, and complete
   document SHA-256 digests.
2. The Stanford--VinBrain radiology-report labeling guideline supplied by its
   authors. Neither that source document nor the schema-mapped textual prompt
   rendering used internally is redistributed. Sanitized model predictions and
   aggregate scores from the comparison remain because they contain no source
   guideline text.
3. RadGraph or other external model checkpoints and their code.
4. Provider APIs, SDKs, raw responses, hidden reasoning content, and service
   infrastructure.

The unredacted local guideline Markdown files are not distributed because they
contain quoted passages from external sources, document identifiers, and
report-like examples. This package contains only author-created, structured
paraphrases of their policy content. The RadGraph publication and schema remain
third-party works and are not relicensed here.

No statement in `LICENSE-DATA` or `LICENSE-CODE` grants rights in these excluded
materials. Product, dataset, and organization names are used only to identify
the experimental conditions and their provenance.
