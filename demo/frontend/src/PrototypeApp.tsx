import { lazy, Suspense, useCallback, useEffect, useState } from "react";
const Glossary = lazy(() => import("./Glossary"));
const PredictScreen = lazy(() => import("./PredictScreen"));
const CompareScreen = lazy(() => import("./CompareScreen"));
const ExploreScreen = lazy(() => import("./ExploreScreen"));
const NotebookScreen = lazy(() => import("./NotebookScreen"));
import { type GlossaryCompound, type GlossaryProtein, type GlossaryDataset, loadGlossary } from "./glossaryData";
import { loadSavedRuns, saveRuns, requestJson, type SavedRun, type VerifiedExample } from "./prototypeData";
import { BrandMark, Symbol, type Screen } from "./PrototypeUI";

const NAV: {id:Screen;label:string}[]=[
  {id:"predict",label:"Predict"},
  {id:"explore",label:"Explore"},
  {id:"glossary",label:"Glossary"},
  {id:"compare",label:"Compare"},
  {id:"notebook",label:"Notebook"},
];
function initialScreen():Screen{
  const hash=window.location.hash.replace(/^#/,"");
  return NAV.some(item=>item.id===hash)?hash as Screen:"predict";
}

export default function PrototypeApp(){
  const [screen,setScreen]=useState<Screen>(initialScreen);
  const [smiles,setSmiles]=useState("");
  const [protein,setProtein]=useState("");
  const [comparePrefill,setComparePrefill]=useState<{a:string;b:string;protein:string}>({a:"",b:"",protein:""});
  const [compareKey,setCompareKey]=useState(0);
  const [backend,setBackend]=useState<"checking"|"online"|"offline">("checking");
  const [examples,setExamples]=useState<VerifiedExample[]>([]);
  const [data,setData]=useState<GlossaryDataset|null>(null);
  const [dataError,setDataError]=useState("");
  const [runs,setRuns]=useState<SavedRun[]>(loadSavedRuns);
  const [storageError,setStorageError]=useState("");

  useEffect(()=>{
    let live=true;
    loadGlossary().then(reference=>{if(live)setData(reference);}).catch(e=>{if(live)setDataError((e as Error).message);});
    const onHash=()=>setScreen(initialScreen());
    window.addEventListener("hashchange",onHash);
    return()=>{live=false;window.removeEventListener("hashchange",onHash);};
  },[]);
  useEffect(()=>{
    try{saveRuns(runs);setStorageError("");}
    catch{setStorageError("Local storage is unavailable. Export history to avoid losing changes.");}
  },[runs]);
  const health=useCallback(async()=>{
    setBackend("checking");
    try{
      const response=await requestJson<{status:string}>("/api/geocpi/health");
      if(response.status!=="ok")throw new Error("Model unhealthy");
      setBackend("online");
      try{
        const listing=await requestJson<{examples:VerifiedExample[]}>("/api/geocpi/examples");
        setExamples(Array.isArray(listing.examples)?listing.examples:[]);
      }catch{setExamples([]);}
    }catch{setBackend("offline");setExamples([]);}
  },[]);
  useEffect(()=>{void health();},[health]);

  function navigate(next:Screen){
    window.location.hash=next;
    setScreen(next);
    window.scrollTo({top:0,behavior:"smooth"});
  }
  function usePair(c:GlossaryCompound,p:GlossaryProtein){
    setSmiles(c.smiles);setProtein(p.sequence);navigate("predict");
  }
  function useCompound(c:GlossaryCompound){setSmiles(c.smiles);navigate("predict");}
  function saveRun(run:SavedRun){setRuns(old=>[run,...old].slice(0,500));}
  function reopen(run:SavedRun){
    if(run.type==="comparison" && run.compoundB){
      setComparePrefill({a:run.compoundA,b:run.compoundB,protein:run.protein});
      setCompareKey(x=>x+1);navigate("compare");
    }else{setSmiles(run.compoundA);setProtein(run.protein);navigate("predict");}
  }
  return <div className="prototype-root">
    <aside className="proto-sidebar">
      <a className="proto-logo" href="#predict" aria-label="GeoFuse CPI home">
        <BrandMark/><span>GeoFuse <em>CPI</em></span>
      </a>
      <div className="proto-menu-section">WORKSPACE</div>
      <nav aria-label="Main navigation" className="proto-navigation">
        {NAV.map(item=><button type="button" key={item.id} className={screen===item.id?"selected":""}
          aria-current={screen===item.id?"page":undefined} onClick={()=>navigate(item.id)}>
          <Symbol name={item.id} size={19}/><span>{item.label}</span>
          {item.id==="notebook" && runs.length>0 && <small>{runs.length}</small>}
        </button>)}
      </nav>
      <div className="proto-sidebar-bottom">
        <span className="proto-build-tag">RESEARCH BUILD / LOCAL</span>
        <button type="button" className="proto-server-status" onClick={()=>void health()} title="Recheck GeoFuse backend">
          <span className={"proto-status-led "+backend}/>
          <span>Bridge :8786 {backend==="online"?"ready":backend==="checking"?"checking":"offline"}</span><Symbol name="reload" size={13}/>
        </button>
        <p>Viewer :8785 · Native 3D requires matched structures</p>
      </div>
    </aside>
    <div className={"proto-main" + (screen==="glossary" || screen==="compare" ? " proto-dark-page" : "")}>
      <header className="proto-mobile-header"><div className="proto-mobile-brand"><BrandMark/>GeoFuse <em>CPI</em></div>
        <span className="proto-build-tag">RESEARCH BUILD</span></header>
      <div className="proto-main-inner">
        <Suspense fallback={<div className="proto-loading-state" role="status">Loading workspace…</div>}>
        {screen==="predict"&&<PredictScreen
          smiles={smiles} protein={protein} setSmiles={setSmiles} setProtein={setProtein}
          examples={examples} glossary={data} backend={backend} refreshBackend={()=>void health()} save={saveRun}/>}
        {screen==="glossary"&&<div className="proto-content proto-glossary-content">
          <Glossary onUsePair={usePair}/>
          {dataError&&<p role="alert" className="proto-muted-note">{dataError}</p>}
        </div>}
        {screen==="compare"&&<CompareScreen key={compareKey} glossary={data}
          initialSmiles={comparePrefill.a||smiles} initialProtein={comparePrefill.protein||protein}
          initialB={comparePrefill.b} backend={backend} save={saveRun}/>}
        {screen==="explore"&&<ExploreScreen data={data} onUseCompound={useCompound}/>}
        {screen==="notebook"&&<NotebookScreen runs={runs} update={setRuns} reopen={reopen} glossary={data}/>}
        {storageError&&<p role="alert" className="proto-storage-warning">{storageError}</p>}
        </Suspense>
      </div>
      <footer className="proto-app-footer">
        <span>GeoFuse CPI · Computational interaction research</span>
        <span>Model estimates are not clinical or experimentally independent validation.</span>
      </footer>
    </div>
  </div>;
}
