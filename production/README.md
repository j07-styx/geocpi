# Production architecture

This directory synchronizes the established local GeoFuse-CPI production models as of 2026-11-25. It supplements, rather than replaces, the historical publication benchmark release.

| Route | Architecture | Input and scope |
| --- | --- | --- |
| Direct 2D | v6 final all-DAVIS refit; two seeds (2931, 2932) | SMILES and amino-acid sequence; pKd, extrapolation flagged |
| Native 3D | V48 frozen v5 backbone + source-trained fourfold residual | Verified native bound geometry; 423D context and 704D geometry |
| Expanded structural inventory | 10,224 retrieval records, 6,744 precomputed research scores | Separate exploratory route, not arbitrary docking or assay certification |

Direct 2D uses frozen ESM-2 650M (1280D) and Morgan (2048D) representations. Protein 1280->96->32 and ligand 2048->128->32 projections feed concatenation of chemical, protein, elementwise product and absolute difference (128D), a 128->64->1 head and a compound-specific or Tanimoto-extrapolated training prior. The two predictions are averaged with a DAVIS pKd floor of 5. The final refit trains on all 30,056 DAVIS pairs and has **no independent held-out score**.

Native V48 uses the earlier frozen v5 backbone, not the new v6 ensemble; its 704->64->32->1 head produces a bounded residual on source-calibrated 2D. It is trained on HiQBind TRAIN349, not on BioLiP3 test labels. See the existing reproduction guides for exact scope and metrics.

## Portable direct 2D inference

From the repository root, in a trusted Python 3.11 environment:

    python -m pip install -r production/requirements.txt
    cd production/direct2d
    python -m zipfile -e v6-inference.zip .
    python serve_portable.py

Health: http://127.0.0.1:8783/api/v2/health. Retrieve example JSON from /api/v2/example and POST its smiles and sequence to /api/v2/predict. Known DAVIS sequences use released frozen features. Novel sequences require the public ESM-2 esm2_t33_650M_UR50D.pt and accompanying contact-regression checkpoint, obtained from the official ESM distribution, with ESM_CHECKPOINT_PATH set if needed. GEOFUSE_2D_PORT overrides the port. Training scripts and original serving code are source snapshots; full retraining requires original DAVIS training inputs and provenance files. The portable bundle omits individual affinity labels and contains learned weights, aggregate training priors and frozen input embeddings. The portable training-metrics endpoint is intentionally unavailable. Checkpoints are trusted repository artifacts only.

## Native 3D

See [native serving instructions](native3d/README.md). Existing reproduce_biolip3.py and reproduce.py remain the self-contained feature-level replay entry points. The full local structural catalog and authentication/frontend application are not included in this architecture-only synchronization.

See [manifest](MANIFEST.json) for checkpoint and source identities. Experimental generalized 3D/SaProt and adaptive V363 are deliberately excluded.
