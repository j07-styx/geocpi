# Reproduce GeoFuse-CPI results

Run from the repository root with Python 3.11 and the dependencies in [requirements-replay.txt](../requirements-replay.txt). The exact CPU reference environment is listed there; no GPU is required for prepared-feature replay.

| Command | Benchmark |
|---|---|
| `python reproduce_biolip3.py` | BioLiP3 37 + 33 historical Ki/Kd cases (pooled 70 is post-hoc) |
| `python reproduce.py` | OpenBind 482 qualifying compounds from 660 frozen inputs |

The scripts run all four source-trained folds and verify each predicted value against its original frozen output (absolute tolerance 1e-5), before opening source affinities. They then recompute metrics and the original 5,000-draw bootstrap intervals. Aggregate reports are saved under `runs/` (ignored by Git); existing outputs are not overwritten. For a new run specify `--out runs/another.json`.

## Source datasets

- BioLiP3: [official experimental affinity TSV](https://zhanggroup.org/BioLiP/lh_3affinity_data/00_Experiments/experiments_affinity.tsv), SHA-256 `c8467ed78b4e78889b417d752e8da4973bfd3a95fb5dc6f1244cafcc8249d0ab`. Original source snapshot dated 2026-11-16. The row identifiers and endpoint kinds are frozen; uncensored Ki/Kd values are interpreted using the original independent assay parser. If the upstream file has changed, the script refuses to substitute newer data. Obtain the original permitted snapshot and pass `--source /path/to/experiments_affinity.tsv`.
- OpenBind EV-A71/CVA16 2A v2: [Zenodo record 22142262](https://doi.org/10.5281/zenodo.22142262), archive SHA-256 `e0d2e38eddf75ebf4247aff0fe28ae15dfa25ecb30deeb4cf950ae184b304a25`. The script takes the median of the finite original experimental pKD replicate values by compound group, as in the original analysis. For a local copy pass `--archive /path/to/OpenBind_EV-A71_2A.zip`.
- HiQBind source dataset: [dataset record](https://doi.org/10.6084/m9.figshare.27430305); training data and full frozen source-fold inputs are not included in these replay bundles.
- PerceiverCPI: [original code](https://github.com/dmis-lab/PerceiverCPI), revision `755f076ef51099a90332fd1ec8437f94e3750c0b`.

The replay will stop if any dataset or bundle checksum differs. Downloads are saved under `data/` and never committed. Use each command with `--inference-only` for offline verification (no experimental affinities opened).

## Bundle contents

- `openbind-replay.zip`: four folds of trained residual state dictionaries (12), 12 LightGBM text calibrators, geometry normalization parameters, 660 frozen 423D/704D feature inputs, compound/scaffold manifest, original frozen model and Perceiver reference predictions.
- `biolip3-replay.zip`: 73 pre-score feature inputs, frozen cohort row selectors, original GeoFuse and both Perceiver comparator outputs. The same four folds are used; 70 cases qualify under original assay rules.
- SHA-256 file manifest within each archive. No experimental numerical affinity labels, reserved test outcomes, user credentials, or executable pickle calibrators are bundled. Torch loads state dictionaries with `weights_only=True`.

## What this reproduces and what it does not

This is real model inference and independent rescoring on the original historical benchmark inputs, not a synthetic demonstration or printing saved metrics. The raw 2D score comes from the original frozen 423D input's final column, the calibrated 2D and 3D outputs are recomputed, and the Perceiver scores are recomputed from frozen reference outputs. It does not independently retrain the GeoFuse 2D backbone, generate raw ESM2/geometry features, retrain the PerceiverCPI comparators, reproduce the source-training selection process, or cover official DAVIS/KIBA/METZ fivefold tasks. These require additional authorized source datasets, weights and protocols. For training on authorized prepared source features use [train.py](../train.py); for native-bound raw inputs see [raw inference](../docs/raw-inference.md). The single-target OpenBind ranking result is not an RMSE win, and the strict primary geometry criterion remains unmet. The BioLiP3 comparison is retrospective, not an equal-input architecture proof.

Local verification on the original source archive bytes: five GeoFuse output arms matched exactly for 660 OpenBind and 73 BioLiP3 inputs; all 165 metric entries and 20 bootstrap intervals matched the published aggregate references. A different machine may have small numerical differences; the scripts require absolute agreement within 1e-5. A fresh Git clone on the original Windows CPU machine reproduced both benchmarks using its installed reference dependencies. BioLiP3 automatic download succeeded; OpenBind returned HTTP 504, but the pinned local archive reproduced all metrics and confidence intervals. The downloader retries transient failures and reports the local-file fallback. Full clean-room reinstall on a different machine and uninterrupted third-party download availability are not established.
