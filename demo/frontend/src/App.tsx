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
};

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
      const response = await api<Prediction>("/api/v2/predict", {
        smiles: smiles.trim(), sequence,
      });
      if (response.status !== "ok" || !Number.isFinite(response.prediction_pKd)) {
        throw new Error("Unexpected prediction response.");
      }
      setResult(response);
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
          <strong>DynaCPI v6</strong>
          <small>SMILES + sequence · 2D-based inference</small>
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
              <p className="example-help">{loadedExample ? "Loaded " + loadedExample + ". Next: " + (EXAMPLES.find(item => item.id === selectedExample)?.label ?? "first sample") + "." :
                "Choose a sample, or click Load example repeatedly to cycle through all six."}</p>
            </div>
            <div className="form-actions">
              <button type="submit" className="primary-button" disabled={busy || connection !== "online"}>
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
              {result ? "● Complete" : busy ? "◌ Running" : "○ Ready"}
            </span>
          </div>
          {result ? <div className="result-content">
            <span className="tiny-overline">PREDICTED AFFINITY</span>
            <div className="result-number">{result.prediction_pKd.toFixed(4)} <small>pKd</small></div>
            <div className="result-meta">
              <span className={"model-label" + (result.known_training_pair ? " warm" : "")}>
                {result.known_training_pair ? "Known training pair" : "Exploratory prediction"}
              </span>
              <span>DynaCPI v6</span>
            </div>
            <p className="result-caveat">{result.notice}</p>
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

      <div className="bottom-note">
        <span><span className="note-symbol">i</span> The molecule preview is generated from SMILES; binding affinity is predicted by the 2D/sequence model, not the 3D viewer.</span>
        <button type="button" onClick={() => setShowDetails(value => !value)}>{showDetails ? "Hide details ↑" : "Model details ↗"}</button>
      </div>
      {showDetails && <section className="research-details">
        <strong>Prediction scope</strong>
        <p>GeoFuse CPI currently uses the frozen DynaCPI v6 all-DAVIS refit with molecular fingerprints and pretrained protein embeddings. All six built-in examples come from the original DAVIS training corpus. The all-data refit has no independent held-out test, so demo scores and new-input predictions do not establish generalization accuracy.</p>
      </section>}
      <footer className="footer"><span>GEOFUSE CPI</span><span>LOCAL RESEARCH INTERFACE</span></footer>
    </main>
  </div>;
}
