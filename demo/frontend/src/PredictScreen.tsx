import { useState } from "react";
import MoleculeViewer from "./MoleculeViewer";
import type { GlossaryDataset } from "./glossaryData";
import { cleanSequence, formatPKd, identifyCompound, identifyProtein, predict, validatePair,
  type ModelPrediction, type SavedRun, type VerifiedExample, newId } from "./prototypeData";
import { InfoTip, PageTitle, Symbol, EmptyMessage } from "./PrototypeUI";

export default function PredictScreen({
  smiles, protein, setSmiles, setProtein, examples, glossary, backend, refreshBackend, save,
}: {
  smiles: string; protein: string;
  setSmiles: (next:string)=>void; setProtein:(next:string)=>void;
  examples: VerifiedExample[]; glossary: GlossaryDataset | null;
  backend: "checking" | "online" | "offline"; refreshBackend: ()=>void;
  save: (run:SavedRun)=>void;
}) {
  const [selectedExample, setSelectedExample] = useState(0);
  const [result, setResult] = useState<ModelPrediction | null>(null);
  const [resultInputs, setResultInputs] = useState<{ smiles:string; protein:string } | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const compound = identifyCompound(glossary, smiles);
  const target = identifyProtein(glossary, protein);
  const sequence = cleanSequence(protein);
  const stale = !!resultInputs && (resultInputs.smiles !== smiles.trim() || resultInputs.protein !== sequence);
  const invalid = validatePair(smiles, protein);
  const displayResult = stale ? null : result;

  function changeSmiles(value:string) { setSmiles(value); setError(""); }
  function changeProtein(value:string) { setProtein(value); setError(""); }
  function loadExample() {
    if (!examples.length) return;
    const example = examples[selectedExample % examples.length];
    setSelectedExample(x=>x+1);
    setSmiles(example.smiles); setProtein(example.sequence);
    setResult(null); setResultInputs(null); setError("");
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (running) return;
    if (invalid) { setError(invalid); return; }
    setRunning(true); setError(""); setResult(null);
    const s=smiles.trim(), p=sequence;
    try {
      const output = await predict(s,p);
      setResult(output); setResultInputs({smiles:s,protein:p});
      const name = `${compound?.name || `SMILES ${s.slice(0,18)}…`} · ${target?.name || `Protein ${p.slice(0,10)}…`}`;
      save({
        id:newId(),type:"prediction",name,timestamp:new Date().toISOString(),
        compoundA:s,protein:p,resultA:output.prediction_pKd,sampleA:output.sample_id,
        notes:"",favorite:false,
      });
    } catch(e) { setError((e as Error).message); }
    finally { setRunning(false); }
  }
  return <div className="proto-content">
    <PageTitle eyebrow="01 / PREDICTION WORKSPACE" title="Predict"
      description="Measure predicted binding affinity for a compound and receptor with verified experimental-bound geometry."
      actions={<span className="proto-scope"><span className="proto-scope-dot"/> SOURCE-VERIFIED MODEL</span>} />

    <div className="proto-predict-grid">
      <section className="proto-card proto-input-card">
        <div className="proto-card-top"><div><span className="proto-section-number">01</span><h2>Input pair</h2></div><span className="proto-mini-label">SMILES + FASTA</span></div>
        <form className="proto-form" onSubmit={event=>void submit(event)}>
          <div className="proto-field-head">
            <label htmlFor="proto-smiles">Compound · SMILES</label><InfoTip label="SMILES">A textual representation of a compound's molecular structure. The backend matches canonical identity against locally verified bound complexes.</InfoTip>
            <span>{smiles.trim().length} / 500</span>
          </div>
          <textarea id="proto-smiles" className="proto-smiles" rows={3} spellCheck={false}
            placeholder="Paste compound SMILES…" value={smiles} onChange={e=>changeSmiles(e.target.value)} />
          <div className="proto-identity">{smiles.trim() && (compound ? <>Compound <strong>{compound.name}</strong> <small>PubChem CID {compound.cid}</small></> : <span>Not identified by exact DAVIS reference match</span>)}</div>

          <div className="proto-field-head">
            <label htmlFor="proto-sequence">Protein · amino-acid sequence</label>
            <InfoTip label="Protein sequence">Enter the full receptor sequence. FASTA headers and whitespace are removed before model inference. The verified 3D backend requires an exact full-sequence match.</InfoTip>
            <span>{sequence.length} / 2048 aa</span>
          </div>
          <textarea id="proto-sequence" className="proto-sequence" rows={6} spellCheck={false}
            placeholder="Paste full receptor sequence or FASTA…" value={protein} onChange={e=>changeProtein(e.target.value)} />
          <div className="proto-identity">{sequence && (target ? <>Protein <strong>{target.name}</strong></> : <span>Not identified by exact DAVIS reference match</span>)}</div>

          <div className="proto-predict-actions">
            <button type="submit" className="proto-button proto-button-primary" disabled={running || backend!=="online"}>
              {running ? "Running inference…" : "Run prediction"} <Symbol name="arrow" size={16}/>
            </button>
            <button className="proto-button proto-button-secondary" type="button" onClick={loadExample}
              disabled={running || !examples.length}>Load verified example</button>
          </div>
          {(error || backend==="offline") && <div className="proto-alert" role="alert">
            {error || "The local model service is offline."}
            {backend==="offline" && <button type="button" onClick={refreshBackend}>Retry connection</button>}
          </div>}
          <div className="proto-model-scope">
            <Symbol name="info" size={16}/>
            <p>Native 3D inference requires exact ligand + full receptor matches in the local set of ~660 experimental complexes. Unsupported pairs return an explicit error; there is no invented pose or silent 2D fallback.</p>
          </div>
        </form>
      </section>

      <div className="proto-output-stack">
        <div className="proto-viewer-shell">
          <div className="proto-viewer-line"><span>LIGAND CONFORMER</span><span>RDKit preview · drag to orbit</span></div>
          <MoleculeViewer smiles={smiles.trim()} />
        </div>
        <section className="proto-score-card" aria-label="Prediction result">
          <div className="proto-score-main">
            <div className="proto-score-label">PREDICTED pKd <InfoTip label="Affinity interpretation">Higher predicted pKd implies stronger modeled binding. pKd = 9 − log₁₀(Kd in nM). This is a computational estimate, not a measured affinity or clinical result.</InfoTip></div>
            {displayResult ? <><div className="proto-score-value">{formatPKd(displayResult.prediction_pKd)}<span>pKd</span></div>
              <div className="proto-score-meta">Native-bound sample <strong>{displayResult.sample_id}</strong> · 2D + 3D verified</div></> :
              <div className="proto-score-placeholder"><strong>—.—</strong><span>{running ? "Running model" : stale ? "Inputs changed; run again" : "Awaiting prediction"}</span></div>}
          </div>
          <div className="proto-score-explain">
            <span className="proto-mini-label">SCORE INTERPRETATION</span>
            <div className="proto-scale"><span/></div>
            <div className="proto-scale-labels"><span>pKd ≤ 5 · weaker</span><span>stronger →</span></div>
            <p>Higher pKd corresponds to lower Kd. The viewer is a ligand-only conformer and is not the bound geometry used by the model.</p>
          </div>
        </section>
      </div>
    </div>
    <div className="proto-under-row">
      <div><strong>2D calibrated features</strong><span>SMILES fingerprint + protein representation</span></div>
      <div className="proto-join">+</div>
      <div><strong>Native-bound 3D residual</strong><span>Experimental ligand–pocket geometry</span></div>
      <div className="proto-join">=</div>
      <div><strong>GeoFuse prediction</strong><span>A single reported affinity estimate</span></div>
    </div>
    {!displayResult && backend==="online" && !running && !invalid && !error &&
      <span className="proto-sr-note">Inputs are ready for model inference.</span>}
  </div>;
}
