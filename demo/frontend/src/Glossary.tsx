import { useEffect, useMemo, useState } from "react";
import "./glossary.css";
import { loadGlossary, type GlossaryCompound, type GlossaryDataset, type GlossaryProtein } from "./glossaryData";

type Row = { compoundIndex: number; proteinIndex: number; kdNm: number };
type Filter = "all" | "quantified" | "cutoff";
type Sort = "strongest" | "compound" | "protein";
const PAGE_SIZE = 20;
const CUTOFF_NM = 10000;

function formatKd(value: number) {
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export default function Glossary({
  onUsePair,
}: {
  onUsePair: (compound: GlossaryCompound, protein: GlossaryProtein) => void;
}) {
  const [data, setData] = useState<GlossaryDataset | null>(null);
  const [error, setError] = useState("");
  const [compoundSearch, setCompoundSearch] = useState("");
  const [proteinSearch, setProteinSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<Sort>("strongest");
  const [page, setPage] = useState(0);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    let active = true;
    loadGlossary().then(dataset => { if (active) setData(dataset); })
      .catch(err => { if (active) setError((err as Error).message); });
    return () => { active = false; };
  }, []);

  const matched = useMemo(() => {
    if (!data) return [];
    const compounds = data.compounds;
    const proteins = data.proteins;
    const cQuery = compoundSearch.trim().toLowerCase();
    const pQuery = proteinSearch.trim().toLowerCase();
    const rows: Row[] = [];

    for (let c = 0; c < compounds.length; c++) {
      if (cQuery && !compounds[c].name.toLowerCase().includes(cQuery)
          && !compounds[c].cid.includes(cQuery)) continue;
      for (let p = 0; p < proteins.length; p++) {
        if (pQuery && !proteins[p].name.toLowerCase().includes(pQuery)) continue;
        const kdNm = data.kdNm[c][p];
        if (filter === "quantified" && kdNm >= CUTOFF_NM) continue;
        if (filter === "cutoff" && kdNm < CUTOFF_NM) continue;
        rows.push({ compoundIndex: c, proteinIndex: p, kdNm });
      }
    }
    rows.sort((a, b) => {
      if (sort === "compound") return compounds[a.compoundIndex].name.localeCompare(compounds[b.compoundIndex].name)
        || a.kdNm - b.kdNm;
      if (sort === "protein") return proteins[a.proteinIndex].name.localeCompare(proteins[b.proteinIndex].name)
        || a.kdNm - b.kdNm;
      return a.kdNm - b.kdNm || a.compoundIndex - b.compoundIndex;
    });
    return rows;
  }, [data, compoundSearch, proteinSearch, filter, sort]);

  const pages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages - 1);
  const shown = matched.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
    } catch {
      setCopied("Could not copy; select the text instead.");
    }
  }

  function changeSearch(value: string, kind: "compound" | "protein") {
    if (kind === "compound") setCompoundSearch(value);
    else setProteinSearch(value);
    setPage(0);
  }

  return <div className="glossary-view">
    <section className="glossary-hero">
      <div>
        <div className="intro-kicker"><span className="intro-spark" /> CPI REFERENCE LIBRARY</div>
        <h1>Interaction <span>glossary.</span></h1>
        <p>Look up known compound–protein pairs by name and inspect their published DAVIS binding-affinity values.</p>
      </div>
      <div className="glossary-stat">
        <span className="tiny-overline">PUBLIC BENCHMARK</span>
        <strong>{data ? (data.compounds.length * data.proteins.length).toLocaleString("en-US") : "—"}</strong>
        <small>DAVIS compound–protein pairs</small>
      </div>
    </section>

    <section className="glossary-panel" aria-label="Compound protein interaction glossary">
      <div className="glossary-panel-title">
        <div className="heading-pair">
          <span className="panel-num">G</span>
          <div><h2>Glossary</h2><p>Compound names · SMILES · protein identities · amino-acid sequences · affinities</p></div>
        </div>
        {data && <span className="glossary-source-badge">DAVIS / Kd nM</span>}
      </div>

      <div className="glossary-controls">
        <label className="glossary-control glossary-search">
          <span>Compound name or PubChem CID</span>
          <input aria-label="Search compound name" placeholder="e.g. Quizartinib" value={compoundSearch}
            onChange={event => changeSearch(event.target.value, "compound")} />
        </label>
        <label className="glossary-control glossary-search">
          <span>Protein name</span>
          <input aria-label="Search protein name" placeholder="e.g. FLT3, EGFR, ABL1" value={proteinSearch}
            onChange={event => changeSearch(event.target.value, "protein")} />
        </label>
        <label className="glossary-control glossary-select">
          <span>Affinity records</span>
          <select aria-label="Filter binding affinities" value={filter} onChange={event => { setFilter(event.target.value as Filter); setPage(0); }}>
            <option value="all">All pairs</option>
            <option value="quantified">Below 10,000 nM</option>
            <option value="cutoff">10,000 nM cutoff</option>
          </select>
        </label>
        <label className="glossary-control glossary-select">
          <span>Sort results</span>
          <select aria-label="Sort glossary entries" value={sort} onChange={event => { setSort(event.target.value as Sort); setPage(0); }}>
            <option value="strongest">Strongest binding</option>
            <option value="compound">Compound A–Z</option>
            <option value="protein">Protein A–Z</option>
          </select>
        </label>
      </div>

      {error ? <div className="glossary-message" role="alert">{error}</div>
        : !data ? <div className="glossary-message">Loading public DAVIS reference data…</div>
        : <>
          <div className="glossary-count">
            <span><strong>{matched.length.toLocaleString("en-US")}</strong> matching pairs
              {matched.length ? ` · displaying ${currentPage * PAGE_SIZE + 1}–${Math.min((currentPage + 1) * PAGE_SIZE, matched.length)}` : ""}
            </span>
            <span>Values are benchmark labels, not GeoFuse predictions.</span>
          </div>
          <div className="glossary-scroll" role="region" tabIndex={0} aria-label="Five-column glossary table, scroll horizontally on small screens">
            <table className="glossary-table">
              <colgroup><col className="col-compound"/><col className="col-smiles"/><col className="col-protein"/><col className="col-sequence"/><col className="col-affinity"/></colgroup>
              <thead><tr>
                <th scope="col">Compound names</th>
                <th scope="col">SMILES</th>
                <th scope="col">Protein name</th>
                <th scope="col">Amino acid sequence</th>
                <th scope="col">Binding affinity value</th>
              </tr></thead>
              <tbody>
                {shown.map(({ compoundIndex, proteinIndex, kdNm }) => {
                  const compound = data.compounds[compoundIndex];
                  const protein = data.proteins[proteinIndex];
                  const isCutoff = kdNm >= CUTOFF_NM;
                  const key = compound.cid + "-" + proteinIndex;
                  return <tr key={key}>
                    <td>
                      <strong className="glossary-drug-name">{compound.name}</strong>
                      <a className="glossary-cid" href={`https://pubchem.ncbi.nlm.nih.gov/compound/${compound.cid}`}
                        target="_blank" rel="noreferrer">PubChem CID {compound.cid} ↗</a>
                      <button type="button" className="glossary-use" onClick={() => onUsePair(compound, protein)}>Use in predictor ↗</button>
                    </td>
                    <td>
                      <code className="glossary-code">{compound.smiles}</code>
                      <button type="button" className="glossary-copy" onClick={() => void copy(compound.smiles, key + "-s")}>
                        {copied === key + "-s" ? "Copied ✓" : "Copy SMILES"}
                      </button>
                    </td>
                    <td><strong className="glossary-protein-name">{protein.name}</strong></td>
                    <td>
                      <details className="glossary-sequence">
                        <summary><code>{protein.sequence.slice(0, 43)}{protein.sequence.length > 43 ? "…" : ""}</code>
                          <span>View full sequence · {protein.sequence.length} aa</span></summary>
                        <code className="glossary-sequence-full">{protein.sequence}</code>
                      </details>
                      <button type="button" className="glossary-copy" onClick={() => void copy(protein.sequence, key + "-p")}>
                        {copied === key + "-p" ? "Copied ✓" : "Copy sequence"}
                      </button>
                    </td>
                    <td>
                      <strong className={`glossary-affinity ${isCutoff ? "cutoff" : ""}`}>
                        {isCutoff ? "≥ 10,000" : formatKd(kdNm)} <small>nM</small>
                      </strong>
                      <span className="glossary-pkd">{isCutoff ? "pKd ≤ 5.000" : `pKd ${(9 - Math.log10(kdNm)).toFixed(3)}`}</span>
                      {isCutoff && <span className="glossary-cutoff-label">Screening cutoff</span>}
                    </td>
                  </tr>;
                })}
                {!shown.length && <tr><td colSpan={5} className="glossary-no-results">
                  No pairs match these names and filters. Try a different compound or protein.
                </td></tr>}
              </tbody>
            </table>
          </div>
          <div className="glossary-pagination">
            <span>Page {currentPage + 1} of {pages}</span>
            <div>
              <button type="button" onClick={() => setPage(0)} disabled={currentPage === 0} aria-label="First glossary page">«</button>
              <button type="button" onClick={() => setPage(Math.max(0, currentPage - 1))} disabled={currentPage === 0}>Previous</button>
              <button type="button" onClick={() => setPage(Math.min(pages - 1, currentPage + 1))} disabled={currentPage >= pages - 1}>Next</button>
              <button type="button" onClick={() => setPage(pages - 1)} disabled={currentPage >= pages - 1} aria-label="Last glossary page">»</button>
            </div>
          </div>
        </>}
    </section>

    <div className="glossary-footnote">
      <strong>How to read the values</strong>
      <p><b>Kd (nM)</b> is the DAVIS benchmark label. A smaller Kd indicates stronger binding; pKd = 9 − log₁₀(Kd in nM).
        Values at 10,000 nM are weak/nonbinding or unobserved screening cutoffs, not precise measurements.
        These are historical dataset labels, not new experiments or model predictions.</p>
      <p>Source: <a href="https://github.com/hkmztrk/DeepDTA/tree/master/data/davis" target="_blank" rel="noreferrer">public DeepDTA / DAVIS dataset ↗</a>.
        Compound names: <a href="https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest" target="_blank" rel="noreferrer">PubChem ↗</a>.
        Selecting “Use in predictor” fills the inputs only; the GeoFuse 3D model still requires a verified matching native-bound complex.</p>
    </div>
  </div>;
}
