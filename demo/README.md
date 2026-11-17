# GeoFuse-CPI demo: source-calibrated 2D + verified native 3D

## Two branches, one prediction

For a **verified exact compound–protein match** to a locally available experimental native-bound complex:

- **2D branch:** frozen DynaCPI v5 features (423D) → source-only fourfold LightGBM calibrator
- **3D branch:** native experimental ligand–protein contacts/angles (704D) → trained bounded residual MLP
- **Fusion:** calibrated 2D prediction + scaled geometry residual → affinity score

`demo/geocpi_bridge.py` exposes the fused inference on `127.0.0.1:8786/api/geocpi/predict`, and routes only exact canonical SMILES **and full receptor-sequence** matches to original frozen 423D/704D label-free inputs.

The bridge's reference set is 660 native-bound OpenBind structures. The source manifest (`private/v51_raw660_structures/raw660.csv`), label-free `private/v51_raw660_RDKIT2025_features_noY.npz`, and fourfold fitted source-only residual/checkpoint files in `runs/v48_train349_source_fourfold_replay` are **not distributed**. Authorized local users can supply their own valid matching files. `DYNACPI_3D_PAPER` can point at a working research root.

The 3D bridge returns HTTP 422 `no_verified_native_pose` for unmatched pairs; **no fake pose or geometry is generated**. The React UI explicitly marks those pairs as **2D-only** when the independently hosted 2D DynaCPI v6 backend is available.

## UI and local auxiliary services

In `demo/frontend`:

```powershell
npm ci
npm run dev
```

Visit `http://127.0.0.1:5174/`. Its Vite proxy routes:
- `/api/geocpi` → `127.0.0.1:8786`: exact-match **fused** 2D+native 3D bridge.
- `/api/v2` → `127.0.0.1:8783`: independently hosted all-DAVIS **2D-only** demo API. This original service is not shipped here.
- `/api/viewer` → `127.0.0.1:8785`: `demo/viewer_service.py` (RDKit gas-phase ligand visualization), runnable separately with `python demo/viewer_service.py`.

To run the native-bound bridge locally after placing appropriate authorized source-only features, experimental structures and trained checkpoints in the research root:

```powershell
python demo/geocpi_bridge.py
```

It requires PyTorch, NumPy, RDKit, joblib, LightGBM, and the private trained source checkpoint files. The separate `demo/backend.py` also provides the older native-geometry example/feature API at port 8784.

**Limitations:** This bridge does not retrieve structures online or dock arbitrary new ligands. Native bound 3D is available for matching local experimental structures only. The OpenBind source outcomes have already been unsealed, so matched-complex examples are not new prospective evaluations. Do not claim that a rendered 3D ligand conformer was fed into the affinity model. Do not expose local services publicly without security hardening.
