# Benchmark evidence

These are immutable aggregate records; historical model names and version identifiers are retained for provenance. See [methods](../docs/methods.md) and the [main results tables](../README.md#results).

| File | Scope |
|---|---|
| biolip3_aggregates.json | Historical BioLiP3 cohorts and controls |
| v28_full_davis_matched_perceiver.json | DAVIS-supervised-source-matched Perceiver comparison |
| openbind2026_single_target_482_aggregate.json | Independent single-target OpenBind evaluation |
| prepared_feature_exact_replay.json | Prepared-feature training and inference parity |
| v51_scientific_audit_and_raw_reproducibility.json | Aggregate metric/CI audit and raw input replay |

Run `python verify.py` to check available aggregate arithmetic; original source hash checks require the separately held research archive. These records are not per-pair predictions or a full downloadable training dataset.
