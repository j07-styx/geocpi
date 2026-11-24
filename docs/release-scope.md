# GeoFuse-CPI public research release

This repository is a deliberately curated public source snapshot, not a copy of the working research directory.

Included: compact model/training/evaluation/source reproducibility code, aggregate benchmark evidence and figures, guard tests, optional React UI and native-bound example API source.

Not included: private assay records, individual protected test predictions, source datasets, checkpoints, ESM2 weights, local virtual environments, research provenance archives, raw PDB/SDF structures, or user-specific launch scripts.

**Research limitations:** The retrospective BioLiP3 full-system comparator is not an equal-input architecture win; real-vs-shuffled geometry there is inconclusive. The independently sourced OpenBind 482-compound test showed ranking but not absolute RMSE improvement; the primary two-control geometry gate failed. DockBind failed its locked minimum-30 structure gate and affinity labels remain sealed.

The demo requires separately acquired authorized pretrained weights and native-bound examples. The normal SMILES/sequence path is a 2D service and is NOT a free-form 3D prediction service.

The original GeoFuse-CPI 2D (v5) and PerceiverCPI author attributions remain with those respective works. No automatic open-source license is asserted until ownership and third-party compatibility have been reviewed.

## Compatibility and citation

Use `geofuse_cpi` for new Python imports. The historical `dynacpi3d` package is a thin compatibility alias, and the old demo environment variable names remain accepted. Result JSON, geometry encoder bytes, original model format strings and archived figures retain their source identifiers. Cite the repository revision and the original dataset/baseline references in the methods document; a paper DOI and license have not been assigned in this release.
