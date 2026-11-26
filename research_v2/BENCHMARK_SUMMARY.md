# GeoFuse-CPI V2.0: consolidated benchmark ledger

**Single frozen checkpoint:** b30fd7f5054ea6352d53c2dc854ce0af9cd7d163970c5c4b4b0b7591772d97f4

**Prediction archive SHA-256:** b8f935e2115ead2b83e247477118adedd38559acf368b80eabafc160240f0555

**Scope:** 15 evaluation cohorts, 9,899 rows across DAVIS/KIBA/METZ and GenSPARC. Overlapping benchmark cohorts are not independent observations.

This file reports results from one checkpoint only. No metric is imported from V499 or any other experimental model. Native expert predictions were replayed from the same checkpoint hash.

## 1. DAVIS, KIBA and METZ: double-cold evaluation

PerceiverCPI comparator values below are matched local reproductions, not the original papers headline table values. Lower RMSE/MAE is better; higher Pearson and C-index is better.

| Dataset | n | V2.0 RMSE | Reproduced PerceiverCPI RMSE | Delta RMSE | V2.0 MAE | V2.0 Pearson | V2.0 C-index |
|---|---:|---:|---:|---:|---:|---:|---:|
| DAVIS | 1339 | 0.6216 | 0.6828 | -0.0611 | 0.3824 | 0.1311 | 0.6052 |
| KIBA | 3442 | 0.7864 | 0.9267 | -0.1402 | 0.5310 | 0.4517 | 0.6356 |
| METZ | 1416 | 0.8797 | 1.0187 | -0.1390 | 0.6779 | 0.4866 | 0.6264 |

## 2. GenSPARC: comparison with published point estimates

Each cohort has published RMSE and Pearson values. Deltas are V2.0 minus published: negative RMSE delta and positive Pearson delta favor V2.0. Published per-interaction predictions were not available, so these are point-estimate comparisons, not paired significance tests.

| Split | Cohort | n | V2.0 RMSE | Published RMSE | Delta RMSE | V2.0 Pearson | Published Pearson | Delta Pearson |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Original | seen both | 591 | 1.2736 | 1.357 | -0.0834 | 0.7783 | 0.748 | +0.0303 |
| Original | unseen compound | 521 | 1.1889 | 1.221 | -0.0321 | 0.7835 | 0.787 | -0.0035 |
| Original | unseen protein | 795 | 1.4668 | 1.551 | -0.0842 | 0.5829 | 0.526 | +0.0569 |
| Original | unseen both | 202 | 1.5527 | 1.552 | +0.0007 | 0.5877 | 0.583 | +0.0047 |
| Sequence-hard | seen both | 265 | 1.0459 | 1.121 | -0.0751 | 0.8232 | 0.805 | +0.0182 |
| Sequence-hard | unseen compound | 169 | 1.2805 | 1.372 | -0.0915 | 0.6565 | 0.631 | +0.0255 |
| Sequence-hard | unseen protein | 106 | 1.5465 | 1.444 | +0.1025 | 0.5824 | 0.642 | -0.0596 |
| Sequence-hard | unseen both | 189 | 1.4055 | 1.624 | -0.2185 | 0.5761 | 0.522 | +0.0541 |
| Structure-hard | seen both | 269 | 1.0445 | 1.141 | -0.0965 | 0.8212 | 0.793 | +0.0282 |
| Structure-hard | unseen compound | 191 | 1.3703 | 1.411 | -0.0407 | 0.6294 | 0.618 | +0.0114 |
| Structure-hard | unseen protein | 161 | 1.4239 | 1.519 | -0.0951 | 0.6365 | 0.582 | +0.0545 |
| Structure-hard | unseen both | 243 | 1.3830 | 1.559 | -0.1760 | 0.6066 | 0.546 | +0.0606 |

**Numerical wins: 20/24 metrics** (12 cohorts times RMSE and Pearson). This is not 24/24 superiority.

### Four metric misses

| Cohort | Metric | V2.0 | GenSPARC published | Gap |
|---|---|---:|---:|---:|
| Original unseen compound | Pearson (higher is better) | 0.7835 | 0.787 | -0.0035 |
| Original unseen both | RMSE (lower is better) | 1.5527 | 1.552 | +0.0007 |
| Sequence-hard unseen protein | RMSE (lower is better) | 1.5465 | 1.444 | +0.1025 |
| Sequence-hard unseen protein | Pearson (higher is better) | 0.5824 | 0.642 | -0.0596 |

## 3. Native 3D expert: same-checkpoint replay

These are retrospective native-geometry evaluations. BioLiP3 pooled 70 is a post-hoc combination of two cohorts; OpenBind is a single-target external set. They do not establish broad multi-target external superiority.

| Cohort | n | 2D RMSE | Native-real RMSE | Shuffled-geometry RMSE | Pocket-only RMSE | Real vs 2D |
|---|---:|---:|---:|---:|---:|---|
| BioLiP3 first cohort | 37 | 1.5209 | 1.2232 | 1.2631 | 1.3158 | improved |
| BioLiP3 second cohort | 33 | 1.6356 | 1.4176 | 1.4289 | 1.4523 | improved |
| BioLiP3 pooled post-hoc | 70 | 1.5760 | 1.3184 | 1.3438 | 1.3818 | improved |
| OpenBind single-target | 482 | 1.7917 | 1.7986 | 1.8222 | 1.9162 | regressed |

Interpretation: pooled BioLiP3 native-real RMSE is 1.3184 versus 1.5760 for 2D (16.35% lower), but OpenBind native-real RMSE is 1.7986 versus 1.7917 for 2D (slightly worse). The 3D benefit is therefore not consistent across these cohorts. No inferential claim is made from the pooled BioLiP3 point estimate alone.

## 4. Independent external validation gate

**Status: BLOCKED_NO_ELIGIBLE_COHORT**. The predeclared gate requires a new source with exact compound/protein/pair and cross-source scaffold/homology checks, assay provenance and endpoint verification, and native pose QA for geometry. No eligible independent multi-target cohort is currently authorized for scoring. Do not describe the current retrospective BioLiP3/OpenBind results as prospective independent validation.

## 5. Claim boundaries

- V2.0 beats the matched reproduced PerceiverCPI comparator on RMSE in the three listed double-cold datasets; those are reproduced baseline comparisons, not original published-value wins.
- GenSPARC comparison is 20/24 numerical metric wins against the papers rounded point estimates, not a universal win over every method in the paper.
- Four GenSPARC metrics remain losses as listed above.
- The 2D predictor and native 3D expert are separately trained components in a fixed hybrid checkpoint; this is not an end-to-end jointly trained 2D+3D network.
- No independent multi-target external validation claim is supported yet.
- Keep this checkpoint and its prediction archive fixed for all headline claims. Any replacement must be retrained and rescored across every benchmark before it can become the single paper model.
