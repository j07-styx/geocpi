# GeoFuse-CPI V2.0 ? frozen research release

One frozen hybrid checkpoint for the reported model results. This is a research release candidate, not an independently validated production replacement.

- SHA-256: `b30fd7f5054ea6352d53c2dc854ce0af9cd7d163970c5c4b4b0b7591772d97f4`
- All 15 shared-task evaluation cohorts are recorded in PAPER_RESULTS.json (9,899 entries; overlapping cohorts are not independent).
- NATIVE_ACCURACY_AUDIT.json recomputes the native arm from the same checkpoint and checksum-pinned BioLiP3 and OpenBind source affinities.
- GenSPARC: 20/24 numerical comparisons to GenSPARC in published Tables 2 and 4, not every method in those tables. Source: https://doi.org/10.1038/s42004-025-01844-0.
- DAVIS/KIBA/METZ comparisons use archived reproduced PerceiverCPI outputs, not original paper table numbers.
- Native real arm: pooled BioLiP3 n=70 RMSE 1.318425; OpenBind n=482 RMSE 1.798589. OpenBind real fails the calibrated-2D RMSE comparison. Report the negative result.
- GenSPARC uses structural tokens, not experimental native coordinates. Native geometry is a separately trained expert with a distinct legacy anchor, not end-to-end joint training.
- Joint cross-source training differs from published protocols; exact entity quarantine is not full scaffold/homology isolation. Historical benchmarks were inspected during research. New independent confirmation is blocked by lack of an eligible cohort.
- Matched-training neural ablations are separate experiments, not V2.0 checkpoint scores.

## Verify the bundle
Run `python verify_release.py` from this directory, then `python verify_release.py --smoke` with torch, numpy, RDKit and LightGBM installed. This checks archive contents, checkpoint identity and finite kinase/native prepared-input predictions. It does not establish new prediction accuracy.

## Kinase inference
The archive contains the one checkpoint and the training-only kinase anchor arrays. Extract locally and use Predictor(checkpoint, anchors) from geofuse_portable_kinase.py. It accepts assay name (davis/kiba/metz), SMILES strings and corresponding 1280-dimensional ESM2-650M embeddings. geofuse_raw_kinase.py provides CPU raw-sequence encoding with the SHA-pinned public ESM2 weights. The deployed V6 architecture is not replaced by this release.

## Remaining reproducibility limits
GenSPARC input preparation and native 423D/704D feature construction are not yet portable end-to-end in this release. SHARED_REPLAY.json documents replay in the original research environment. The existing native replay bundles at ../reproduction contain the label-free prepared geometry features; their original affinity sources are fetched separately by the repository's reproduction scripts. No source affinity datasets or private numeric labels are shipped here.
