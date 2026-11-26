# Results

## Evaluation overview

GeoFuse-CPI V2.0 was evaluated on 15 benchmark cohorts comprising 9,899 cohort-level test entries across DAVIS, KIBA, METZ and GenSPARC. The cohort counts are not a count of 9,899 unique independent compounds or interactions: the GenSPARC original, sequence-hard and structure-hard test partitions are separate evaluation settings and may overlap in their underlying source records. The reported checkpoint was held fixed throughout the consolidated evaluation (checkpoint SHA-256: b30fd7f5054ea6352d53c2dc854ce0af9cd7d163970c5c4b4b0b7591772d97f4; prediction archive SHA-256: b8f935e2115ead2b83e247477118adedd38559acf368b80eabafc160240f0555). All headline values below are taken from that checkpoint's frozen result ledger. Experimental variants developed later are excluded.

Binding-affinity errors are reported on each benchmark's native target scale. RMSE values should therefore be compared within a dataset or against a comparator evaluated on the same cases, not pooled across datasets with different affinity definitions and distributions.

## 2D predictor on DAVIS, KIBA and METZ

On the double-cold test partitions, the GeoFuse-CPI 2D predictor achieved lower RMSE than the archived, locally reproduced PerceiverCPI comparator on all three datasets (Table 1). RMSE reductions were 0.0611 on DAVIS, 0.1402 on KIBA and 0.1390 on METZ. The GeoFuse-CPI concordance index was 0.6052, 0.6356 and 0.6264, respectively.

| Dataset | Test n | GeoFuse-CPI RMSE | Reproduced PerceiverCPI RMSE | RMSE difference | GeoFuse-CPI MAE | GeoFuse-CPI Pearson r | GeoFuse-CPI C-index |
|---|---:|---:|---:|---:|---:|---:|---:|
| DAVIS | 1,339 | 0.6216 | 0.6828 | -0.0611 | 0.3824 | 0.1311 | 0.6052 |
| KIBA | 3,442 | 0.7864 | 0.9267 | -0.1402 | 0.5310 | 0.4517 | 0.6356 |
| METZ | 1,416 | 0.8797 | 1.0187 | -0.1390 | 0.6779 | 0.4866 | 0.6264 |

The PerceiverCPI values in Table 1 are archived local reproductions evaluated on matched rows; they are not the original PerceiverCPI paper's headline values. A 5,000-draw crossed protein-group/chemical-scaffold bootstrap gave row-weighted pooled RMSE-difference intervals (GeoFuse-CPI minus archived PerceiverCPI) of [-0.1159, -0.0013] for DAVIS, [-0.2333, -0.0533] for KIBA and [-0.2394, -0.0445] for METZ. These are descriptive, unadjusted intervals from the evaluated splits. Under macro/group-weighted resampling, the corresponding intervals included zero for DAVIS and KIBA, but not METZ. In an additional floor-matched PerceiverCPI sensitivity analysis on DAVIS, the pooled interval was [-0.1012, 0.0127], which included zero. The point estimates are favorable, but the evidence is not uniformly robust to comparator construction and aggregation.

## Comparison with published GenSPARC results

The fixed GeoFuse-CPI kinase predictor was also evaluated on the 12 published GenSPARC affinity cohorts spanning the original, sequence-hard and structure-hard settings, each with seen-both, unseen-compound, unseen-protein and unseen-both partitions. Across the 12 cohorts, GeoFuse-CPI had a numerically better RMSE and/or Pearson correlation than the corresponding published GenSPARC point estimate in 20 of 24 metric comparisons (Table 2). This count is a comparison with GenSPARC's reported values only; it is not a claim of superiority over every method in the GenSPARC paper.

| Evaluation setting | Test partition | n | GeoFuse-CPI RMSE | GenSPARC RMSE | GeoFuse-CPI Pearson r | GenSPARC Pearson r |
|---|---|---:|---:|---:|---:|---:|
| Original | Seen both | 591 | 1.2736 | 1.357 | 0.7783 | 0.748 |
| Original | Unseen compound | 521 | 1.1889 | 1.221 | 0.7835 | 0.787 |
| Original | Unseen protein | 795 | 1.4668 | 1.551 | 0.5829 | 0.526 |
| Original | Unseen both | 202 | 1.5527 | 1.552 | 0.5877 | 0.583 |
| Sequence-hard | Seen both | 265 | 1.0459 | 1.121 | 0.8232 | 0.805 |
| Sequence-hard | Unseen compound | 169 | 1.2805 | 1.372 | 0.6565 | 0.631 |
| Sequence-hard | Unseen protein | 106 | 1.5465 | 1.444 | 0.5824 | 0.642 |
| Sequence-hard | Unseen both | 189 | 1.4055 | 1.624 | 0.5761 | 0.522 |
| Structure-hard | Seen both | 269 | 1.0445 | 1.141 | 0.8212 | 0.793 |
| Structure-hard | Unseen compound | 191 | 1.3703 | 1.411 | 0.6294 | 0.618 |
| Structure-hard | Unseen protein | 161 | 1.4239 | 1.519 | 0.6365 | 0.582 |
| Structure-hard | Unseen both | 243 | 1.3830 | 1.559 | 0.6066 | 0.546 |

Four metric comparisons were not numerically better than the published GenSPARC values: Pearson r on the original unseen-compound partition (0.7835 versus 0.787), RMSE on the original unseen-both partition (1.5527 versus 1.552), and both RMSE and Pearson r on the sequence-hard unseen-protein partition (1.5465 versus 1.444; 0.5824 versus 0.642). The sequence-hard unseen-protein cohort is the clearest remaining weakness. Published per-interaction predictions were not available for a paired reanalysis, and the published table values are rounded; these comparisons are descriptive point-estimate comparisons rather than paired significance tests.

## Native-structure expert evaluation

The native-structure component is a separately trained residual expert conditioned on the frozen 2D representation; it is not an end-to-end jointly trained 2D-plus-3D network. Its geometry descriptor represents ligand–pocket atom-pair chemistry, radial distances and angular/contact information. The expert was assessed using native experimental bound poses and geometry controls.

### Historical BioLiP3 cohorts

The first BioLiP3 cohort contained 37 complexes and the second contained 33 eligible complexes. Both cohorts were drawn from the same underlying BioLiP3 source and should not be interpreted as independent assay-database replications. In each cohort, the native-geometry expert had a lower RMSE than the calibrated 2D arm. The post-hoc pooled 70-complex RMSE was 1.3184 for native geometry, compared with 1.5760 for calibrated 2D, 1.3438 for shuffled geometry and 1.3818 for the pocket-only control (Table 3).

| BioLiP3 cohort | n | Calibrated 2D RMSE | Native-real RMSE | Shuffled-geometry RMSE | Pocket-only RMSE |
|---|---:|---:|---:|---:|---:|
| First cohort | 37 | 1.5209 | 1.2232 | 1.2631 | 1.3158 |
| Second cohort | 33 | 1.6356 | 1.4176 | 1.4289 | 1.4523 |
| Post-hoc pooled | 70 | 1.5760 | 1.3184 | 1.3438 | 1.3818 |

A separate full-system comparator replay on the post-hoc pooled BioLiP3 set gave RMSE 1.8624 and C-index 0.4570 for the original 12-member DAVIS-pretrained PerceiverCPI ensemble, compared with RMSE 1.3184 and C-index 0.7285 for GeoFuse-CPI with native-real geometry. This is a retrospective comparison of complete systems, not an equal-input architecture comparison: GeoFuse-CPI uses ESM-2-derived features and experimentally bound ligand–protein poses, whereas the PerceiverCPI comparator does not receive the same native-pose input. The pooled comparison is also post hoc and comes from one source database.

Although native-real geometry had the best point RMSE in both BioLiP3 cohorts, the historical real-versus-shuffled geometry-specific MAE and C-index uncertainty intervals included zero. Thus, these small retrospective cohorts do not establish a statistically resolved, geometry-specific improvement over shuffled geometry.

### OpenBind 2026 single-target external cohort

OpenBind provided an independently sourced experimental campaign for EV-A71/CVA16 2A protease. Of 925 original X-ray ligand–protein events, 923 passed the initial structure/pose quality screen. Source-only chemical and scaffold filters retained 660 compound structures; 482 of these had qualifying measured pKd values spanning 264 scaffolds. Predictions and model inputs were frozen before the pKd outcomes were accessed. The test therefore provides a temporally blinded, source-independent evaluation for one protease family, but not a multi-target validation.

On the 482 measured compounds, the native-real expert had RMSE 1.7986 and C-index 0.6640. It ranked above the shuffled-geometry control by C-index, but its absolute error was not improved over the calibrated 2D arm (RMSE 1.7917) and was substantially worse than the raw 2D arm (RMSE 0.8803) and the original PerceiverCPI comparator (RMSE 1.2885). The raw and calibrated 2D arms are different prediction stages and are both shown to make the calibration behaviour transparent.

| OpenBind model arm | RMSE | MAE | C-index |
|---|---:|---:|---:|
| Raw GeoFuse-CPI 2D | 0.8803 | 0.7319 | 0.5094 |
| Calibrated GeoFuse-CPI 2D | 1.7917 | 1.6388 | 0.6572 |
| Native-real 3D expert | 1.7986 | 1.6409 | 0.6640 |
| Shuffled-geometry control | 1.8222 | 1.6437 | 0.6247 |
| Pocket-only control | 1.9162 | 1.7601 | 0.6527 |
| Original PerceiverCPI full 12-model comparator | 1.2885 | — | 0.4658 |

For the predeclared geometry-specific contrasts, native-real versus shuffled geometry improved C-index by 0.0392 (5,000-resample scaffold-cluster 95% CI [0.0203, 0.0562]), and native-real versus pocket-only reduced MAE by 0.1192 (95% CI [-0.1522, -0.0894]). However, the native-real versus shuffled MAE difference was -0.0029 (95% CI [-0.0333, 0.0305]), which includes zero. Because the primary criterion required a favorable MAE interval over both controls, the primary geometry criterion was not met. The native-real model also overpredicted mean affinity by approximately 1.62 pKd units, indicating a substantial calibration problem on this source.

## Reproducibility checks

The consolidated benchmark ledger and native audit refer to the same frozen checkpoint and prediction archive. The shared-feature replay reproduced predictions with a maximum absolute difference of 6.6 × 10^-7 across the 15 cohorts. The independent native audit reproduced the native arms from the same checkpoint and SHA-pinned source labels. Separately, the raw-input audit re-encoded all 660 OpenBind source structures in a fresh Windows Python 3.11 environment: all original 704-dimensional geometry and 166-dimensional side features matched exactly, and all five final prediction arms remained within the prespecified 0.03 pKd tolerance (maximum difference 0.0189). This supports raw-input parity for the tested OpenBind inputs and environment, not a fully hermetic clean-room installation or full raw-input retraining.

# Limitations

## Generalization and benchmark comparability

The results do not establish universal superiority over current CPI models. The 20/24 GenSPARC count compares GeoFuse-CPI with GenSPARC's published RMSE and Pearson point estimates only. It does not compare against every method in that paper, does not use paired per-interaction GenSPARC predictions, and does not provide a significance test. The four remaining metric misses include both metrics on the sequence-hard unseen-protein cohort, which is the most consequential unresolved weakness. The original unseen-both RMSE difference is very small (1.5527 versus 1.552) and should not be described as a meaningful win or loss beyond the reported numerical comparison.

The DAVIS, KIBA and METZ PerceiverCPI comparisons use archived local reproductions on matched evaluation rows, not the original PerceiverCPI publication tables. The model and comparator were not established as fully matched in every training, pretraining and optimization detail. In particular, the DAVIS floor-matched sensitivity interval includes zero, and macro/group-weighted uncertainty intervals include zero for DAVIS and KIBA. These results support favorable point estimates and useful reproduced comparisons, but not an unqualified claim of statistically robust superiority under all aggregation choices.

The benchmark cohorts are not all independent. The 15 cohort counts sum to 9,899 evaluation entries, but the GenSPARC original, sequence-hard and structure-hard partitions may overlap in underlying records. BioLiP3's two evaluated subsets originate from the same source database, and their pooled 70-complex metric is post hoc. The pooled BioLiP3 result must not be presented as an independent replication or as evidence from two independent assay databases.

## Limits of the 3D evidence

The native-geometry expert has not demonstrated a consistent absolute-affinity improvement across external settings. The BioLiP3 point estimates favour native-real geometry over calibrated 2D and shuffled geometry, but the historical real-versus-shuffled MAE and C-index intervals include zero. On OpenBind, native-real geometry improves C-index over shuffled geometry, yet the prespecified primary MAE contrast against shuffled geometry is inconclusive. Native-real RMSE is slightly worse than calibrated 2D and markedly worse than raw 2D and the original PerceiverCPI comparator. The 3D branch therefore cannot be claimed to improve absolute binding-affinity prediction consistently.

The OpenBind evaluation is independent at the source/assay-campaign level but covers only EV-A71/CVA16 2A protease. It cannot establish generalization to unrelated protein families, kinases or broad target classes. It also uses experimentally determined ligand-bound structures. This is a structure-conditioned rescoring experiment, not a prospective pose-free screening evaluation: a valid bound ligand pose and compatible protein structure are required for the native-geometry arm. The approximately 1.62-pKd mean overprediction on OpenBind further shows that calibration transfer remains unresolved.

The BioLiP3 cohorts are small (37 and 33 complexes), retrospective, and sourced from the same database. BioLiP3 combines Ki and Kd measurements after conversion to pAffinity, so assay heterogeneity may remain. Its pooled statistic is calculated from pooled squared errors and is not the mean of the two cohort RMSE values. The post-hoc pooled result is useful as a descriptive summary, but it should not be treated as a pre-registered independent test.

## Architecture and training limitations

The 2D predictor and native-geometry expert are separate components. The native expert is a bounded residual model conditioned on a frozen 2D representation and a legacy source-trained anchor; the reported system is not an end-to-end jointly optimized 2D/3D fusion network. Consequently, the current results do not show that jointly learning 2D and 3D representations is superior to late residual conditioning, nor do they isolate the contribution of each modality under fully matched pretraining and optimization.

The protein representation relies on pretrained ESM-2-derived features, while the molecular branch uses a pretrained chemical prior. These representations provide useful prior information but introduce dependencies on external pretrained resources and their training corpora. The current evaluation does not fully quantify the contribution of each pretraining source or establish that the model's gains arise from the proposed fusion design alone.

The current cross-source training and evaluation setup does not provide complete scaffold-level and protein-homology isolation across every source. Exact-entity quarantine is not equivalent to global chemical-scaffold and protein-sequence/structure-family quarantine. Historical benchmark results were inspected during model development, so they are not untouched prospective tests. Any additional tuning on these cohorts would make subsequent scores exploratory and should not be used to strengthen confirmatory claims.

## Reproducibility and deployment scope

The public release supports checkpoint verification, prepared-feature replay and aggregate benchmark reproduction. The shared replay reproduces the stored cohort predictions to numerical tolerance, and the OpenBind raw-input audit reproduces the tested OpenBind features and predictions within the fixed tolerance. However, this does not amount to a fully hermetic clean-room reinstall on a separate machine, full retraining from raw source structures, or end-to-end raw-input parity for every benchmark. GenSPARC and native feature preparation are not yet fully portable in the public release; some source training labels, backbone weights and source arrays remain outside the repository for provenance and access reasons.

The native-geometry service should not be represented as a general 3D predictor for arbitrary SMILES and protein sequences. Without a verified compatible experimental complex pose, the native-geometry residual cannot be assumed to be available or valid. The ordinary sequence/SMILES path is a 2D prediction path; native 3D inference has additional structural-input requirements.

## Independent validation still required

The predeclared independent validation gate remains blocked because no additional eligible multi-target cohort has passed the required source, assay, entity-overlap, scaffold/homology and structural-pose checks. DockBind and PLINDER preflights did not meet the minimum structurally valid family-cold feasibility threshold, and their affinity labels remain sealed. A future confirmatory study should use a new source with at least 30 distinct eligible complexes as a feasibility floor, justify sample size and power before scoring, verify endpoint and assay provenance, enforce cross-source scaffold and protein-homology separation, freeze all model and comparator predictions before label access, and report paired group-aware uncertainty for all prespecified contrasts.

## Appropriate scope of the present claims

The evidence supports a promising 2D kinase-affinity predictor with favourable reproduced comparisons on DAVIS, KIBA and METZ, and favourable numerical comparisons with published GenSPARC values on 20 of 24 reported metrics. It also supports a technically reproducible native-geometry expert with encouraging retrospective BioLiP3 results and a limited ranking signal on one independent OpenBind target family. It does not yet support claims of universal CPI superiority, statistically established geometry-specific affinity improvement, end-to-end jointly trained 2D/3D fusion superiority, prospective pose-free 3D screening, or independent multi-target external validation.

## References cited in these sections

1. Zhang, Y., Ishitani, R., Takemoto, M. & Tomita, A. Generalizable compound protein interaction prediction with a model incorporating protein structure aware and compound property aware language model representations. *Communications Chemistry* **9**, 37 (2026). https://doi.org/10.1038/s42004-025-01844-0
2. Nguyen, N.-Q., Jang, G., Kim, H. & Kang, J. Perceiver CPI: a nested cross-attention network for compound-protein interaction prediction. *Bioinformatics* **39**(1), btac731 (2023). https://doi.org/10.1093/bioinformatics/btac731

*Editorial note: add the primary citations for DAVIS, KIBA, METZ, BioLiP3, OpenBind and HiQBind to the manuscript's master bibliography when these sections are integrated. The comparisons and caveats above are intentionally phrased to match the frozen evidence ledger; do not merge these values with later experimental variants.*