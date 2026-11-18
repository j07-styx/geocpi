import { useMemo, useState } from "react";
import type { GlossaryDataset } from "./glossaryData";
import { exportJson, type SavedRun } from "./prototypeData";
import { EmptyMessage, PageTitle, Symbol, InfoTip } from "./PrototypeUI";

type Filter = "all" | "prediction" | "comparison" | "favorites";

export default function NotebookScreen({ runs, update, reopen, glossary }:{
  runs:SavedRun[];update:(next:SavedRun[])=>void;reopen:(run:SavedRun)=>void;glossary:GlossaryDataset|null;
}) {
  const [filter,setFilter]=useState<Filter>("all");
  const [search,setSearch]=useState("");
  const [editing,setEditing]=useState<string|null>(null);
  const [draftName,setDraftName]=useState("");
  const [draftNotes,setDraftNotes]=useState("");
  const [confirmDelete,setConfirmDelete]=useState<string|null>(null);
  const visible=useMemo(()=>runs.filter(run=>
    (filter==="all"||filter==="favorites"&&run.favorite||run.type===filter)
    && (run.name+" "+run.notes+" "+run.sampleA+" "+run.sampleB).toLowerCase().includes(search.toLowerCase())
  ),[runs,filter,search]);

  function startEditing(run:SavedRun){setEditing(run.id);setDraftName(run.name);setDraftNotes(run.notes);}
  function saveEdit(){
    update(runs.map(run=>run.id===editing?{...run,name:draftName.trim()||run.name,notes:draftNotes.slice(0,5000)}:run));
    setEditing(null);
  }
  function toggleFavorite(id:string){update(runs.map(run=>run.id===id?{...run,favorite:!run.favorite}:run));}
  function remove(id:string){update(runs.filter(run=>run.id!==id));setConfirmDelete(null);setEditing(null);}
  function targetName(seq:string){return glossary?.proteins.find(p=>p.sequence===seq)?.name||`Sequence · ${seq.length} aa`;}
  return <div className="proto-content">
    <PageTitle eyebrow="05 / RESEARCH NOTEBOOK" title="Notebook"
      description="A real, local record of completed predictions and comparisons. Rename, annotate, revisit, and export your experiments."
      actions={<button type="button" className="proto-button proto-button-secondary" disabled={!runs.length}
        onClick={()=>exportJson("geofuse-cpi-experiments.json",{version:1,exportedAt:new Date().toISOString(),records:runs})}>
        <Symbol name="download" size={16}/> Export JSON</button>}/>
    <div className="proto-notebook-note"><Symbol name="info" size={16}/> Stored privately in this browser's local storage. Clearing browser data deletes this history; use Export for a portable backup.</div>
    <section className="proto-card proto-notebook">
      <div className="proto-notebook-toolbar">
        <div className="proto-filter-chips" role="group" aria-label="Filter experiments">
          {(["all","prediction","comparison","favorites"] as const).map(f=>
            <button key={f} type="button" className={filter===f?"is-active":""} onClick={()=>setFilter(f)}>
              {f==="all"?"All experiments":f==="prediction"?"Predictions":f==="comparison"?"Comparisons":"Favorites"}
              <span>{f==="all"?runs.length:f==="favorites"?runs.filter(r=>r.favorite).length:runs.filter(r=>r.type===f).length}</span>
            </button>)}
        </div>
        <input aria-label="Search notebook history" placeholder="Search experiments and notes…" value={search} onChange={e=>setSearch(e.target.value)}/>
      </div>
      {visible.length ? <div className="proto-table-scroll"><table className="proto-notebook-table">
        <thead><tr><th>Experiment</th><th>Type</th><th>Target protein</th><th>Result</th><th>Saved</th><th>Actions</th></tr></thead>
        <tbody>{visible.map(run=><tr key={run.id}>
          <td><button className={"proto-favorite "+(run.favorite?"on":"")} type="button" onClick={()=>toggleFavorite(run.id)} title={run.favorite?"Remove favorite":"Favorite"} aria-label={run.favorite?"Remove favorite":"Favorite"}><Symbol name="star" size={16}/></button>
            <strong>{run.name}</strong>{run.notes&&<small className="proto-run-notes">{run.notes.slice(0,65)}{run.notes.length>65?"…":""}</small>}
          </td>
          <td><span className={"proto-type-pill "+run.type}>{run.type}</span></td>
          <td>{targetName(run.protein)}</td>
          <td className="proto-run-value">
            <strong>{run.type==="comparison" && run.resultB!==undefined?`${run.resultA.toFixed(3)} → ${run.resultB.toFixed(3)}`:run.resultA.toFixed(3)}</strong>
            <small>{run.type==="comparison" && run.resultB!==undefined?`Δ ${(run.resultB-run.resultA).toFixed(3)} pKd`:"predicted pKd"}</small>
          </td>
          <td>{new Date(run.timestamp).toLocaleString()}</td>
          <td className="proto-run-actions"><button type="button" title="Edit name and notes" onClick={()=>startEditing(run)}>Edit</button>
            <button type="button" title="Load into predictor" onClick={()=>reopen(run)}>Reopen</button>
            <button type="button" title="Delete record" onClick={()=>setConfirmDelete(run.id)}>Delete</button>
          </td>
        </tr>)}</tbody></table></div> : <EmptyMessage title={runs.length?"No matching experiments":"No experiments saved yet"}
          description={runs.length?"Change your search or filters.":"Completed model predictions and supported comparisons will appear here automatically. Nothing is pre-filled."}/>}
    </section>
    {editing&&<div className="proto-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setEditing(null);}}>
      <div className="proto-dialog" role="dialog" aria-modal="true" aria-label="Edit experiment">
        <h2>Edit research record</h2>
        <label htmlFor="edit-run-name">Experiment name</label><input id="edit-run-name" value={draftName} onChange={e=>setDraftName(e.target.value)}/>
        <label htmlFor="edit-run-notes">Research notes <InfoTip label="Experiment notes">Notes are stored only in this browser. They are user-authored and do not change the historical model prediction.</InfoTip></label>
        <textarea id="edit-run-notes" rows={6} maxLength={5000} value={draftNotes} onChange={e=>setDraftNotes(e.target.value)}/>
        <div className="proto-dialog-actions"><button type="button" className="proto-button proto-button-secondary" onClick={()=>setEditing(null)}>Cancel</button><button type="button" className="proto-button proto-button-primary" onClick={saveEdit}><Symbol name="save" size={15}/> Save changes</button></div>
      </div>
    </div>}
    {confirmDelete&&<div className="proto-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setConfirmDelete(null);}}>
      <div className="proto-dialog" role="alertdialog" aria-modal="true" aria-label="Confirm deletion">
        <h2>Delete this record?</h2><p>It will be removed from your browser's notebook. This action cannot be undone.</p>
        <div className="proto-dialog-actions"><button className="proto-button proto-button-secondary" type="button" onClick={()=>setConfirmDelete(null)}>Cancel</button><button className="proto-button proto-button-danger" type="button" onClick={()=>remove(confirmDelete)}>Delete record</button></div>
      </div>
    </div>}
  </div>;
}
