# Prompt templates

These JSON files preserve the task structure and output contracts used in the
study while replacing report-bearing values with double-braced placeholders.
They are templates, not verbatim API request dumps. In particular, no report
text, indexed text, gold entity surface string, discrepancy context, or raw
response is included.

Templates 04 and 08 include the exact report-independent `ENTITY_SCHEMA` and
`RELATION_SCHEMA` constants from the executed held-out runner; template 09
contains their exact concatenation. The public template source checksums are
recorded in `metadata/provenance.json`. These templates describe the common
interface and do not capture all provider-specific request wrappers.

The discrepancy-candidate templates show that each proposal used every error
instance in the selected stratum. Relation proposals additionally received all
currently correct relations for the implicated predicate or predicates as
true-positive contrasts.

Template 06 uses `relation_discrepancy` field names. The historical runner used
causal-error labels for the same bookkeeping fields, but the study performed no
causal identification; this terminology normalization does not alter the
selection or candidate-evaluation procedure.
