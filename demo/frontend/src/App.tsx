import { useEffect, useState } from "react";
import demoExamples from "./demoExamples.json";
import MoleculeViewer from "./MoleculeViewer";

type Connection = "checking" | "online" | "offline";
type Prediction = {
  status: string;
  prediction_pKd: number;
  known_training_pair: boolean;
  protein_in_original_davis: boolean;
  compound_in_original_davis: boolean;
  seed_prediction_std: number;
  notice: string;
  geometry_used?: boolean;
  geometry_source?: string;
  calibrated_2d_pKd?: number;
  sample_id?: string;
};

type NativeExample = { sample_id: string; smiles: string; sequence: string; source: string };

type Example = {
  id: string; label: string; target: string; smiles: string;
  sequence: string; source: string;
};
const EXAMPLES: Example[] = demoExamples;
const FIRST_EXAMPLE = EXAMPLES[0]?.id ?? "";

async function api<T>(path: string, body?: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: body ? "POST" : "GET",
      headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new Error("Cannot reach the prediction backend. Launch GeoFuse CPI with start.bat.");
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error((data as { error?: string } | null)?.error ?? "Backend returned HTTP " + response.status);
  }
  return data as T;
}
function cleanSequence(raw: string) {
  return raw.split(/\r?\n/).filter(line => !line.trim().startsWith(">"))
    .join("").replace(/\s+/g, "").toUpperCase();
}

export default function App() {
  const [smiles, setSmiles] = useState("");
  const [protein, setProtein] = useState("");
  const [connection, setConnection] = useState<Connection>("checking");
  const [nativeConnection, setNativeConnection] = useState<Connection>("checking");
  const [nativeExamples, setNativeExamples] = useState<NativeExample[]>([]);
  const [nativeExampleIndex, setNativeExampleIndex] = useState(0);
  const [result, setResult] = useState<Prediction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selectedExample, setSelectedExample] = useState(FIRST_EXAMPLE);
  const [loadedExample, setLoadedExample] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const sequence = cleanSequence(protein);
  const valid = smiles.trim().length > 0 && smiles.trim().length <= 500
    && sequence.length >= 1 && sequence.length <= 2048
    && /^[ACDEFGHIKLMNPQRSTVWYX]+$/.test(sequence);

  async function health() {
    setConnection("checking");
    setNativeConnection("checking");
    try {
      const native = await api<{status: string}>("/api/geocpi/health");
      setNativeConnection(native.status === "ok" ? "online" : "offline");
      if (native.status === "ok") {
        const examples = await api<{examples: NativeExample[]}>("/api/geocpi/examples");
        setNativeExamples(examples.examples);
      }
    } catch { setNativeConnection("offline"); }
    try {
      const data = await api<{ status: string; service: string }>("/api/v2/health");
      setConnection(data.status === "ok" && data.service === "dynacpi-v6-all-davis" ? "online" : "offline");
    } catch {
      setConnection("offline");
    }
  }
  useEffect(() => { void health(); }, []);

  function loadExample() {
    const index = EXAMPLES.findIndex(item => item.id === selectedExample);
    if (index < 0) return;
    const item = EXAMPLES[index];
    setSmiles(item.smiles);
    setProtein(item.sequence);
    setLoadedExample(item.label);
    setResult(null);
    setError("");
    // Each press loads the chosen preset, then prepares the next one.
    setSelectedExample(EXAMPLES[(index + 1) % EXAMPLES.length].id);
  }

  function loadNativeExample() {
    if (!nativeExamples.length) return;
    const item = nativeExamples[nativeExampleIndex % nativeExamples.length];
    setSmiles(item.smiles);
    setProtein(item.sequence);
    setLoadedExample("Verified native-bound complex " + item.sample_id);
    setNativeExampleIndex(n => n + 1);
    setResult(null);
    setError("");
  }

  async function predict() {
    if (busy) return;
    setError("");
    if (!valid) {
      setError("Enter a valid SMILES and protein sequence (1–2048 supported amino acids).");
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      let fused: Prediction | null = null;
      if (nativeConnection === "online") {
        try {
          fused = await api<Prediction>("/api/geocpi/predict", { smiles: smiles.trim(), sequence });
          if (!fused.geometry_used || !Number.isFinite(fused.prediction_pKd)) throw new Error("Invalid fused 3D result.");
        } catch (err) {
          if (!(err as Error).message.startsWith("No experimentally bound complex matches")) throw err;
        }
      }
      if (fused && fused.geometry_used) {
        setResult(fused);
      } else {
        if (connection !== "online") throw new Error("No verified 3D structure for this pair and 2D service unavailable.");
        const base = await api<Prediction>("/api/v2/predict", { smiles: smiles.trim(), sequence });
        if (base.status !== "ok" || !Number.isFinite(base.prediction_pKd)) throw new Error("Invalid 2D result.");
        setResult({ ...base, geometry_used: false });
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="/" aria-label="GeoFuse CPI home">
        <span className="brand-mark"><span/><span/><span/></span>
        <span><strong>GeoFuse <b>CPI</b></strong><small>MOLECULAR AFFINITY RESEARCH</small></span>
      </a>
      <button type="button" className={"connection " + connection} onClick={() => void health()} title="Check backend connection">
        <span className="indicator"/>
        {connection === "online" ? "Model online" : connection === "checking" ? "Connecting…" : "Model offline"}
        <span className="refresh-sign">↻</span>
      </button>
    </header>

    <main className="main-content">
      <section className="intro">
        <div>
          <div className="intro-kicker"><span className="intro-spark"/> AFFINITY PREDICTION WORKSPACE</div>
          <h1>Compound + protein. <span>One prediction.</span></h1>
          <p>Enter a SMILES and protein sequence, visualize the molecule, and predict binding affinity.</p>
        </div>
        <div className="intro-side">
          <span className="tiny-overline">MODEL</span>
          <strong>GeoFuse-CPI</strong>
          <small>{nativeConnection === "online" ? "2D + verified native 3D fusion enabled" : "2D branch only — 3D service offline"}</small>
        </div>
      </section>

      <div className="dashboard">
        <section className="entry-panel">
          <div className="panel-top">
            <div className="heading-pair">
              <span className="panel-num">01</span>
              <div><h2>Prediction inputs</h2><p>Provide your compound–protein pair</p></div>
            </div>
          </div>
          <form className="input-form" onSubmit={event => { event.preventDefault(); void predict(); }}>
            <div className="form-group">
              <div className="form-label"><label htmlFor="smiles">Compound SMILES</label><span>{smiles.length} / 500</span></div>
              <input id="smiles" autoComplete="off" spellCheck={false} placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O" value={smiles}
                onChange={event => { setSmiles(event.target.value); setResult(null); setLoadedExample(""); }} />
            </div>
            <div className="form-group">
              <div className="form-label"><label htmlFor="protein">Protein amino-acid sequence</label><span>{sequence.length} / 2048 aa</span></div>
              <textarea id="protein" rows={8} spellCheck={false} placeholder="Paste a protein sequence or FASTA record…" value={protein}
                onChange={event => { setProtein(event.target.value); setResult(null); setLoadedExample(""); }} />
              <p className="field-support">FASTA headers and line breaks are accepted.</p>
            </div>

            <div className="example-area">
              <div className="example-top"><strong>Try a DAVIS example</strong><span>{EXAMPLES.length} different pairs</span></div>
              <div className="example-controls">
                <select id="example-select" aria-label="Choose the next example compound and protein" value={selectedExample}
                  onChange={event => setSelectedExample(event.target.value)}>
                  {EXAMPLES.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}
                </select>
                <button type="button" onClick={loadExample} className="demo-button">
                  Load example <span aria-hidden="true">↗</span>
                </button>
              </div>
              <button className="native-example-button" type="button" disabled={nativeConnection !== "online" || !nativeExamples.length} onClick={loadNativeExample}>Load verified 3D complex ({nativeExamples.length || 0})</button>
              <p className="example-help">{loadedExample ? "Loaded " + loadedExample + ". Next: " + (EXAMPLES.find(item => item.id === selectedExample)?.label ?? "first sample") + "." :
                "Choose a sample, or click Load example repeatedly to cycle through all six."}</p>
            </div>
            <div className="form-actions">
              <button type="submit" className="primary-button" disabled={busy || (connection !== "online" && nativeConnection !== "online")}>
                {busy ? "Running model…" : "Predict affinity"} <span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>
          {(error || connection === "offline") && <div role="alert" className="form-error">
            {error || "Prediction backend offline. Start GeoFuse CPI using start.bat."}
          </div>}
        </section>

        <div className="output-column">
          <MoleculeViewer smiles={smiles} />
        <section className="result-panel" aria-label="Binding affinity result">
          <div className="panel-top">
            <div className="heading-pair">
              <span className="panel-num">03</span>
              <div><h2>Prediction result</h2><p>Estimated compound–protein affinity</p></div>
            </div>
            <span className={"result-status" + (result ? " ready" : "")}>
              {result ? (result.geometry_used ? "● Fused 2D + 3D" : "● 2D only") : busy ? "◌ Running" : "○ Ready"}
            </span>
          </div>
          {result ? <div className="result-content">
            <span className="tiny-overline">PREDICTED AFFINITY</span>
            <div className="result-number">{result.prediction_pKd.toFixed(4)} <small>pKd</small></div>
            <div className="result-meta">
              <span className="model-label">{result.geometry_used ? "GeoFuse native-bound fusion" : "DynaCPI v6 — 2D only"}</span>
              {result.sample_id && <span>Structure: {result.sample_id}</span>}
            </div>
            {result.geometry_used && typeof result.calibrated_2d_pKd === "number" && <p className="branch-numbers">2D source-calibrated branch: <strong>{result.calibrated_2d_pKd.toFixed(4)}</strong> · Geometry-conditioned fused score: <strong>{result.prediction_pKd.toFixed(4)}</strong></p>}
            <p className="result-caveat">{result.geometry_used ? "Verified experimental ligand–protein bound pose used in the 704D geometry branch. Historical matched-complex demo, not a new blind validation." : "2D-only exploratory result. No experimentally bound pose matched this compound + protein; 3D fusion was NOT run."}</p>
            <button type="button" className="clear-button" onClick={() => { setResult(null); setError(""); }}>Clear result ↗</button>
          </div> : <div className="result-empty">
            <div className="empty-mark" aria-hidden="true">◎</div>
            <strong>{busy ? "Calculating affinity…" : "Ready to predict"}</strong>
            <p>{busy ? "Running the trained inference model." : "Fill both input fields or load one of the six examples, then predict."}</p>
          </div>}
          <div className="result-footer">
            <span className="tiny-overline">IMPORTANT</span>
            <p>Training-set examples are in-sample demonstrations, not independent validation. Results on new compounds or proteins are exploratory.</p>
          </div>
        </section>
        </div>
      </div>

      <section className="branch-pipeline" aria-label="GeoFuse two branch architecture">
        <div className="branch-box"><strong>2D branch</strong><span>SMILES fingerprint + ESM-2 protein context</span><small>423 features · source-calibrated affinity</small></div>
        <div className="branch-box"><strong>3D branch</strong><span>Experimental ligand–protein pocket contacts</span><small>704 features · geometric residual</small></div>
        <div className="branch-fusion"><strong>Fusion</strong><span>2D calibrated prediction + bounded 3D residual → one affinity score</span><small>{result?.geometry_used ? "Both branches executed for this matched complex" : "3D branch only executes for a verified native-bound match"}</small></div>
      </section>
      <div className="bottom-note">
        <span><span className="note-symbol">i</span> The molecule visualizer is independent. GeoFuse uses real 3D ligand–pocket geometry only when an exact experimental compound–protein match exists; otherwise the result is explicitly 2D-only.</span>
        <button type="button" onClick={() => setShowDetails(value => !value)}>{showDetails ? "Hide details ↑" : "Model details ↗"}</button>
      </div>
      {showDetails && <section className="research-details">
        <strong>Prediction scope</strong>
        <p>The GeoFuse 3D branch is the frozen source-trained HiQBind349 fourfold geometry residual, paired with a source-calibrated 423D DynaCPI v5 branch. For verified OpenBind crystal complexes, the exact compound and complete protein sequence select precomputed native geometry. Those OpenBind affinities have already been unsealed, so the demo is not a new prospective or independent test. Ordinary DAVIS examples and unmatched inputs run DynaCPI v6 2D only. The molecule visualizer is not the 3D model input.</p>
      </section>}
      <footer className="footer"><span>GEOFUSE CPI</span><span>LOCAL RESEARCH INTERFACE</span></footer>
    </main>
  </div>;
}
