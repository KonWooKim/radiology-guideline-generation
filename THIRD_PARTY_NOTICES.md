# Third-party materials and exclusions

This package intentionally excludes the following third-party materials:

1. IU X-Ray/Open-i report text and images. Users must obtain them from their
   original distributor and comply with its terms. Report-bearing study artifacts
   use text references that are resolved only against separately obtained,
   hash-checked reports.
2. The Stanford--VinBrain radiology-report labeling guideline supplied by its
   authors. Neither that source document nor the schema-mapped textual prompt
   rendering used internally is redistributed. Sanitized model predictions and
   aggregate scores from the comparison remain because they contain no source
   guideline text.
3. RadGraph or other external model checkpoints. The repository includes the
   study's checkpoint-interface code and a small reference-entity modification
   patch. The original model implementation and runtime must be obtained separately.
   Upstream copyright and licensing notices apply to patch context.
4. Provider APIs, SDKs, hidden reasoning content, and service infrastructure.
   Model final-answer content and usage metadata are included to the extent the
   contributors hold rights, subject to provider terms.

The full expert-written guidelines and actual Human v1 inputs can be reconstructed
privately from the bundles. IU-derived passages are represented by text references.
Quotations attributed in those documents to the RadGraph paper remain third-party
material and are not relicensed as newly authored prose. The privately supplied
original Author manual is not included, even as a reconstructable encoding.

No statement in `LICENSE-DATA` or `LICENSE-CODE` grants rights in these excluded
materials. Product, dataset, and organization names are used only to identify
the experimental conditions and their provenance.
