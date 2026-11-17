# GeoFuse-CPI demonstration interface

This folder contains the React+Vite UI, a standalone **molecule visualization service**, and a separate native-bound 3D research example API. It is distributed as source, **not** a complete portable affinity-prediction deployment.

## Frontend

From `demo/frontend`:

```powershell
npm ci
npm run dev
```

Open `http://127.0.0.1:5174/`. The frontend proxies:
- `/api/v2` to `127.0.0.1:8783`: a **separate DynaCPI v6 2D SMILES+sequence affinity backend not included** in this public repository.
- `/api/viewer` to `127.0.0.1:8785`: `demo/viewer_service.py` (run with `python demo/viewer_service.py` in an environment with RDKit).

The viewer produces RDKit-generated ligand coordinates for display only. These are **not measured protein-bound poses** and **not used for affinity prediction**.

## Native-bound 3D research backend

`demo/backend.py` provides a separate localhost native-bound example API on port 8784. It requires privately held, authorized TRAIN349-trained model checkpoints in `runs/v48_train349_source_fourfold_replay` and label-free example features in `private/external37_NO_Y.npz` under the repo root. Those files and the original ESM/DAVIS weights are **not shipped** here. Run `python demo/backend.py` only after providing the corresponding dependencies and authorized files.

The current main frontend is the SMILES/sequence 2D interface with a visual ligand conformer, rather than a native-bound protein–ligand 3D inference interface. Source code for the 3D API is provided for research reproducibility, not an end-to-end demo for arbitrary inputs.

All services bind to localhost and require additional security hardening before public deployment.
