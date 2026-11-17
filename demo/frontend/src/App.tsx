import { useEffect, useState } from "react";
import MoleculeViewer from "./MoleculeViewer";

type Connection = "checking" | "online" | "offline";
type Prediction = {
  status: string;
  prediction_pKd: number;
  geometry_used: boolean;
  sample_id: string;
};
type NativeExample = { sample_id: string; smiles: string; sequence: string; source: string };

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
  const [nativeConnection, setNativeConnection] = useState<Connection>("checking");
  const [nativeExamples, setNativeExamples] = useState<NativeExample[]>([]);
  const [nativeExampleIndex, setNativeExampleIndex] = useState(0);
  const [result, setResult] = useState<Prediction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadedExample, setLoadedExample] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const sequence = cleanSequence(protein);
  const valid = smiles.trim().length > 0 && smiles.trim().length <= 500
    && sequence.length >= 1 && sequence.length <= 2048
    && /^[ACDEFGHIKLMNPQRSTVWYX]+$/.test(sequence);

  async function health() {
    setNativeConnection("checking");
    try {
      const native = await api<{status: string}>("/api/geocpi/health");
      setNativeConnection(native.status === "ok" ? "online" : "offline");
      if (native.status === "ok") {
        const examples = await api<{examples: NativeExample[]}>("/api/geocpi/examples");
        setNativeExamples(examples.examples);
      }
    } catch { setNativeConnection("offline"); }
  }
  useEffect(() => { void health(); }, []);

  function loadExample() {
    if (!nativeExamples.length) return;
    const item = nativeExamples[nativeExampleIndex % nativeExamples.length];
    setSmiles(item.smiles);
    setProtein(item.sequence);
    setLoadedExample(item.sample_id);
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
      const fused = await api<Prediction>("/api/geocpi/predict", {
        smiles: smiles.trim(), sequence,
      });
      if (fused.status !== "ok" || fused.geometry_used !== true
          || !Number.isFinite(fused.prediction_pKd)) {
        throw new Error("GeoFuse did not return a valid fused 2D + 3D prediction.");
      }
      setResult(fused);
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
      <button type="button" className={"connection " + nativeConnection} onClick={() => void health()} title="Check backend connection">
        <span className="indicator"/>
        {nativeConnection === "online" ? "Model online" : nativeConnection === "checking" ? "Connecting…" : "Model offline"}
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
          <small>2D + native 3D geometry · fused inference</small>
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
              <div className="example-controls">
                <button type="button" onClick={loadExample} className="demo-button"
                  disabled={nativeConnection !== "online" || !nativeExamples.length}>
                  Load example <span aria-hidden="true">↗</span>
                </button>
              </div>
              <p className="example-help">
                {loadedExample
                  ? "Loaded example " + loadedExample + "."
                  : "Examples use experimental bound complexes so both model branches can run."}
              </p>
            </div>
            <div className="form-actions">
              <button type="submit" className="primary-button" disabled={busy || nativeConnection !== "online"}>
                {busy ? "Running model…" : "Predict affinity"} <span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>
          {(error || nativeConnection === "offline") && <div role="alert" className="form-error">
            {error || "GeoFuse model backend offline. Start GeoFuse CPI using START_GEOFUSE_3D.bat."}
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
              {result ? "● Complete" : busy ? "◌ Running" : "○ Ready"}
            </span>
          </div>
          {result ? <div className="result-content">
            <span className="tiny-overline">PREDICTED AFFINITY</span>
            <div className="result-number">{result.prediction_pKd.toFixed(4)} <small>pKd</small></div>
            <p className="result-caveat">GeoFuse-CPI 2D + experimental-bound 3D fusion.
              Structure: {result.sample_id}. Research demonstration, not prospective validation.</p>
            <button type="button" className="clear-button" onClick={() => { setResult(null); setError(""); }}>Clear result ↗</button>
          </div> : <div className="result-empty">
            <div className="empty-mark" aria-hidden="true">◎</div>
            <strong>{busy ? "Calculating affinity…" : "Ready to predict"}</strong>
            <p>{busy ? "Running the trained inference model." : "Enter both inputs or load an example, then predict."}</p>
          </div>}
          <div className="result-footer">
            <span className="tiny-overline">IMPORTANT</span>
            <p>A matching experimental protein–ligand bound structure is required. No invented 3D poses or silent 2D fallbacks.</p>
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
        <span><span className="note-symbol">i</span> The molecular preview is visual only. Actual GeoFuse predictions require a matched experimental ligand–protein bound pose.</span>
        <button type="button" onClick={() => setShowDetails(value => !value)}>{showDetails ? "Hide details ↑" : "Model details ↗"}</button>
      </div>
      {showDetails && <section className="research-details">
        <strong>Prediction scope</strong>
        <p>GeoFuse-CPI fuses a source-calibrated 423D DynaCPI v5 branch with a 704D native ligand–pocket geometry residual. The current local structure library has 660 OpenBind experimental bound complexes. The backend matches canonical SMILES and full receptor sequence and rejects unmatched pairs rather than substituting a separate 2D predictor. OpenBind assay outcomes were previously unsealed, so these examples are historical demonstrations. RDKit ligand visualization is separate from the 3D model input.</p>
      </section>}
      <footer className="footer"><span>GEOFUSE CPI</span><span>LOCAL RESEARCH INTERFACE</span></footer>
    </main>
  </div>;
}
