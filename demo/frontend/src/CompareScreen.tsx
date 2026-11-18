import { useEffect, useMemo, useState } from "react";
import type { GlossaryDataset } from "./glossaryData";
import { cleanSequence, formatPKd, identifyCompound, identifyProtein, predict,
  newId, requestJson, validatePair, type ModelPrediction, type SavedRun } from "./prototypeData";
import { InfoTip, PageTitle, Symbol } from "./PrototypeUI";

type CompareExample = {
  sequence: string;
  compound_a: { sample_id:string; smiles:string };
  compound_b: { sample_id:string; smiles:string };
  source: string;
};

function Score({ name, result, error, busy }: {name:string;result:ModelPrediction|null;error:string;busy:boolean}) {
  return <div className="proto-compare-score">
    <span className="proto-mini-label">PREDICTED pKd</span>
    <strong>{result ? formatPKd(result.prediction_pKd) : "—.—"}</strong>
    <span className="proto-compare-score-note">{busy ? "Calculating…" : error ? "Unavailable" : result ? `Verified complex: ${result.sample_id}` : `Awaiting ${name}`}</span>
    {error && <p className="proto-compare-error">{error}</p>}
  </div>;
}

export default function CompareScreen({ glossary, initialSmiles, initialProtein, initialB, backend, save }:{
  glossary:GlossaryDataset|null;initialSmiles:string;initialProtein:string;initialB:string;backend:"checking"|"online"|"offline";save:(r:SavedRun)=>void;
}) {
  const [sequenceRaw,setSequenceRaw] = useState(initialProtein);
  const [a,setA] = useState(initialSmiles);
  const [b,setB] = useState(initialB);
  const [aResult,setAResult] = useState<ModelPrediction|null>(null);
  const [bResult,setBResult] = useState<ModelPrediction|null>(null);
  const [aError,setAError] = useState("");
  const [bError,setBError] = useState("");
  const [busy,setBusy] = useState(false);
  const [examples,setExamples] = useState<CompareExample[]>([]);
  const [loadError,setLoadError] = useState("");
  const [version,setVersion] = useState(0);
  const [ranVersion,setRanVersion] = useState(-1);
  const sequence=cleanSequence(sequenceRaw);
  const aName=identifyCompound(glossary,a)?.name||"Compound A";
  const bName=identifyCompound(glossary,b)?.name||"Compound B";
  const proteinName=identifyProtein(glossary,sequence)?.name;
  const stale=version!==ranVersion;
  const hasBoth=!stale && aResult!==null && bResult!==null;
  const delta=hasBoth ? bResult!.prediction_pKd-aResult!.prediction_pKd : null;

  useEffect(()=>{
    let active=true;
    requestJson<{examples:CompareExample[]}>("/api/geocpi/compare-examples")
      .then(x=>{if(active)setExamples(x.examples||[]);})
      .catch(e=>{if(active)setLoadError((e as Error).message);});
    return()=>{active=false;};
  },[]);
  const validA=useMemo(()=>validatePair(a,sequenceRaw),[a,sequenceRaw]);
  const validB=useMemo(()=>validatePair(b,sequenceRaw),[b,sequenceRaw]);
  const change=(setter:(value:string)=>void,value:string)=>{
    setter(value);setVersion(n=>n+1);setAResult(null);setBResult(null);setAError("");setBError("");
  };

  function loadPair(index:number){
    const item=examples[index];
    if(!item)return;
    setSequenceRaw(item.sequence);setA(item.compound_a.smiles);setB(item.compound_b.smiles);
    setAResult(null);setBResult(null);setAError("");setBError("");
    setVersion(n=>n+1);
  }

  async function runComparison(){
    if(busy)return;
    if(validA||validB){setAError(validA||"");setBError(validB||"");return;}
    setBusy(true);setAError("");setBError("");setAResult(null);setBResult(null);
    const s=sequence,aValue=a.trim(),bValue=b.trim(),runVersion=version;
    const outputs=await Promise.allSettled([predict(aValue,s),predict(bValue,s)]);
    const ra=outputs[0].status==="fulfilled"?outputs[0].value:null;
    const rb=outputs[1].status==="fulfilled"?outputs[1].value:null;
    setAResult(ra);setBResult(rb);setRanVersion(runVersion);
    if(outputs[0].status==="rejected")setAError(String((outputs[0].reason as Error)?.message||"Prediction A failed."));
    if(outputs[1].status==="rejected")setBError(String((outputs[1].reason as Error)?.message||"Prediction B failed."));
    if(ra&&rb){
      save({id:newId(),type:"comparison",name:`${aName} vs ${bName} · ${proteinName||"same target"}`,
        timestamp:new Date().toISOString(),compoundA:aValue,compoundB:bValue,
        protein:s,resultA:ra.prediction_pKd,resultB:rb.prediction_pKd,
        sampleA:ra.sample_id,sampleB:rb.sample_id,notes:"",favorite:false});
    }
    setBusy(false);
  }

  return <div className="proto-content">
    <PageTitle eyebrow="04 / COMPARATIVE WORKSPACE" title="Compare" description="Two real model calls. One receptor. See what changes in predicted affinity when you change the compound."
      actions={<span className="proto-scope"><span className="proto-scope-dot"/> SAME TARGET · TWO LIGANDS</span>} />

    <section className="proto-card proto-compare-target">
      <div className="proto-field-head"><label htmlFor="compare-protein">Shared target · full receptor sequence</label>
        <InfoTip label="Exact target">Both compounds are scored against the same exact full protein sequence. Each ligand also needs its own matching experimental-bound pose.</InfoTip>
        <span>{sequence.length} / 2048 aa</span></div>
      <textarea id="compare-protein" rows={3} spellCheck={false} value={sequenceRaw}
        placeholder="Paste or load the same protein sequence for both compounds…"
        onChange={e=>change(setSequenceRaw,e.target.value)} />
      <div className="proto-compare-target-bottom">
        <span>{proteinName ? `Known protein: ${proteinName}` : "Full receptor identity required; FASTA accepted"}</span>
        <div className="proto-compare-example">
          {examples.length ? <select aria-label="Load a verified comparison pair" value="" onChange={e=>loadPair(Number(e.target.value))}>
            <option value="" disabled>Load two verified compounds…</option>
            {examples.map((item,i)=><option value={i} key={item.compound_a.sample_id}>
              Pair {i+1} · {item.compound_a.sample_id} vs {item.compound_b.sample_id}
            </option>)}
          </select> : <span>{loadError ? "Example service unavailable" : "Loading verified pairs…"}</span>}
        </div>
      </div>
    </section>

    <section className="proto-compare-layout" aria-label="Pair comparison">
      <div className="proto-card proto-compound-compare a">
        <div className="proto-compare-top"><span>COMPOUND A</span><span>01 / 02</span></div>
        <label htmlFor="compare-a">Compound SMILES</label>
        <textarea id="compare-a" rows={4} spellCheck={false} value={a} placeholder="Enter first compound SMILES…" onChange={e=>change(setA,e.target.value)}/>
        <span className="proto-compare-name">{identifyCompound(glossary,a)?.name ?? "Exact name unknown"}</span>
        <Score name="compound A" result={stale?null:aResult} error={stale?"":aError} busy={busy}/>
      </div>
      <div className="proto-delta-panel">
        <span className="proto-mini-label">Δ pKd (B − A)</span>
        <strong>{delta===null?"—.—":(delta>0?"+":"")+delta.toFixed(3)}</strong>
        <p>{delta===null?"Run both verified pairs to compare.":"Higher pKd predicts stronger binding. "+(delta>0?"B is predicted stronger.":delta<0?"A is predicted stronger.":"Both predictions match.")}</p>
        <div className="proto-delta-divider"/>
        <small>Comparative prediction only. Not causal evidence of why affinity changes.</small>
      </div>
      <div className="proto-card proto-compound-compare b">
        <div className="proto-compare-top"><span>COMPOUND B</span><span>02 / 02</span></div>
        <label htmlFor="compare-b">Compound SMILES</label>
        <textarea id="compare-b" rows={4} spellCheck={false} value={b} placeholder="Enter second compound SMILES…" onChange={e=>change(setB,e.target.value)}/>
        <span className="proto-compare-name">{identifyCompound(glossary,b)?.name ?? "Exact name unknown"}</span>
        <Score name="compound B" result={stale?null:bResult} error={stale?"":bError} busy={busy}/>
      </div>
    </section>
    <div className="proto-compare-footer">
      <p>{(validA||validB)?"Both inputs require valid SMILES and a complete protein sequence.":"Comparison requires two native-bound compound–target matches; unsupported pairs are reported independently."}</p>
      <button type="button" className="proto-button proto-button-primary" onClick={()=>void runComparison()} disabled={busy||backend!=="online"}>
        {busy?"Running both predictions…":"Compare compounds"} <Symbol name="arrow" size={16}/>
      </button>
    </div>
    {loadError && !examples.length && <p className="proto-muted-note">Verified comparison examples are unavailable: {loadError}. You can still enter two pairs manually.</p>}
  </div>;
}
