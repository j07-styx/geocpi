# GeoFuse CPI — functional frontend prototype

This is a **working React/TypeScript/Vite implementation** on top of the established GeoFuse CPI backend, built from the user's November 2026 design references. It is not a static mockup. It intentionally uses a focused left navigation and **separate pages** instead of stacking every feature on one enormous dashboard.

## Workspaces

- **Predict** — SMILES + full protein sequence input; exact DAVIS name identification when available; verified native-bound example loader; POST to the real GeoFuse fused-inference backend; predicted pKd and matched sample; error states; real RDKit/Three.js **ligand-only conformer** viewer with orbit/reset/zoom.
- **Explore** — actual live compound metadata from PubChem and reviewed human protein records from UniProt; direct source and PubMed search links. Randomized source-backed discovery; no made-up journal articles, scores or biological interactions. Requires access to those external APIs.
- **Glossary** — 30,056 DAVIS pairs across 68 compounds and 442 protein entries, five requested columns, search, pagination, source links, full sequence expansion/copy and model-input handoff. Sort by strongest binding (lowest Kd), weakest binding (highest Kd), compound, or protein; filter 10,000 nM cutoffs.
- **Compare** — one exact full receptor, two compounds, two **actual** fused-inference requests, independent error reporting and **ΔpKd = pKd(B) − pKd(A)**. The added `GET /api/geocpi/compare-examples` route provides 5 pairs of distinct native-bound ligands that share the same full receptor sequence. These examples do not contain fabricated affinity values.
- **Notebook** — successful prediction and comparison records automatically saved to this browser's `localStorage`; search/filter, rename, add notes, favorites, reopen inputs, delete with confirmation, export JSON. No invented past experiments. This is *browser-local* persistence, not cross-device account sync.

Small explanatory info popovers provide context about SMILES, pKd, receptor sequences and the science.

## Start locally

From `demo/frontend`:

```powershell
npm ci
npm run dev
```

Open on the same PC:

- Predictor: `http://127.0.0.1:5174/#predict`
- Explore: `http://127.0.0.1:5174/#explore`
- Glossary: `http://127.0.0.1:5174/#glossary`
- Compare: `http://127.0.0.1:5174/#compare`
- Notebook: `http://127.0.0.1:5174/#notebook`

The Vite proxy routes `/api/geocpi/*` to port **8786** and `/api/viewer/*` to port **8785**. The additional legacy port **8783** is not used for fused predictions. The bridge needs the private local assets and `DYNACPI_3D_PAPER` described in `demo/README.md`. Launch the backend **once**, not with multiple competing terminals.

To compile frontend code:

```powershell
npm run build
```

## Scientific integrity

- A prediction is an actual backend response. Neither the displayed score nor the matched structural ID are synthesized.
- The bridge supports **only pairs for which an exact canonical SMILES + full receptor sequence match** is in the authorized local set of approximately 660 native-bound experimental complexes. Unknown pairs return HTTP **422**. It is not a general ligand docking engine.
- The Three.js visualizer displays a **ligand-only generated conformer** from the RDKit service. It is **not** the protein-bound pose fed to the model. Full protein–ligand complex visuals and binding animations should only be implemented after connecting actual structural files, residues and coordinates.
- The DAVIS reference labels are historical `Kd (nM)`, not model predictions. `pKd = 9 - log10(Kd in nM)`. `Kd = 10,000 nM` is a weak/unobserved **screening cutoff**, displayed as **≥10,000 nM / pKd ≤ 5** rather than a precise assay measurement.
- Comparing two predictions is **not causal evidence** that a ligand modification created the difference.
- PubChem and UniProt live records include source links; the app never substitutes fictional literature or fake result values when their APIs are unreachable.
- This is a computational research tool, **not a diagnostic or clinical service**, and the historic native-bound example dataset must not be passed off as prospective independent validation.

## Technology and implementation notes

The frontend uses **React 19, TypeScript, Vite 8, Three.js + OrbitControls, accessible HTML inputs, native CSS tokens and scoped components**. Page components are lazy-loaded to reduce initial bundle work; the molecular viewer's 3D renderer is isolated to the Predict page. Additional frameworks such as Tailwind may be added if they solve a concrete maintainability or UI problem, but are not necessary to make this prototype functional.

Files: `PrototypeApp.tsx` (shell/navigation), `PrototypeUI.tsx` (shared elements), `PredictScreen.tsx`, `CompareScreen.tsx`, `ExploreScreen.tsx`, `NotebookScreen.tsx`, existing `Glossary.tsx`, `MoleculeViewer.tsx`, `prototypeData.ts`, `prototype.css`, and `demo/geocpi_bridge.py` (real supported comparison examples).

## Verification on built-diff12 — 2026-11-18

- `npm run build` passes TypeScript and Vite production compile.
- `python -m py_compile demo/geocpi_bridge.py` passes.
- Backend request for native-bound pair A returned **7.367886 pKd**, sample `A71EV2A-x7096a`, `geometry_used=true`.
- Pair B on the **same full protein** returned **7.209864 pKd**, sample `A71EV2A-x7190a`, `geometry_used=true`.
- Their computed **ΔpKd (B-A) = −0.158022**. An unmatched pair returned **HTTP 422**.
- Browser smoke test in isolated Microsoft Edge profile passed loading an actual example, rendering its prediction, saving/renaming in notebook, loading a verified comparison, rendering its ΔpKd and saving it, filtering the real Glossary, weakest-first sorting/cutoff, live PubChem/UniProt cards, and verifying no document overflow at emulated 390 px width.
- Evidence log on built-diff12 Desktop: `geofuse-prototype-ui-tests.txt`. Browser screenshots are also on that Desktop, named `geofuse-prototype-*.png`.

**Unfinished future features:** accurate protein-bound complex visualization and trajectory animation from real 3D files; a server-backed multi-user experiment notebook; broader user-specified target/compound support via a validated structural-data workflow; more robust API rate limiting/cache and a deployable secure production environment. These must not be represented as already available.
