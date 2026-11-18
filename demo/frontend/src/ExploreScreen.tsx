import { useEffect, useMemo, useState } from "react";
import type { GlossaryCompound, GlossaryDataset } from "./glossaryData";
import { loadPubChem, type DiscoveryItem } from "./prototypeData";
import { PageTitle, Symbol, EmptyMessage, InfoTip } from "./PrototypeUI";

type ProteinDiscovery = { accession: string; name: string; gene: string; length: number; url: string; };
const GENE_CANDIDATES = ["EGFR","BRAF","KIT","ABL1","FLT3","AAK1","MTOR","JAK2","SRC","FGFR1"];
async function uniprot(gene:string):Promise<ProteinDiscovery>{
  const query=encodeURIComponent(`(gene_exact:${gene}) AND (organism_id:9606) AND (reviewed:true)`);
  const res=await fetch(`https://rest.uniprot.org/uniprotkb/search?query=${query}&format=json&size=1`);
  if(!res.ok)throw new Error(`UniProt returned HTTP ${res.status}`);
  type UniProtResult = { primaryAccession:string; genes?: Array<{geneName?:{value:string}}>;
    sequence?:{length:number}; proteinDescription?:{recommendedName?:{fullName?:{value:string}}} };
  const x=await res.json() as { results?: UniProtResult[] };
  const row=x.results?.[0];
  if(!row || row.genes?.[0]?.geneName?.value?.toUpperCase()!==gene.toUpperCase())throw new Error(`No reviewed human UniProt entry found for ${gene}`);
  return {accession:row.primaryAccession,gene,name:row.proteinDescription?.recommendedName?.fullName?.value||gene,
    length:row.sequence?.length||0,url:`https://www.uniprot.org/uniprotkb/${row.primaryAccession}/entry`};
}

export default function ExploreScreen({data,onUseCompound}:{
  data:GlossaryDataset|null;onUseCompound:(compound:GlossaryCompound)=>void;
}){
  const [search,setSearch]=useState("");
  const [compounds,setCompounds]=useState<DiscoveryItem[]>([]);
  const [proteins,setProteins]=useState<ProteinDiscovery[]>([]);
  const [error,setError]=useState("");
  const [proteinError,setProteinError]=useState("");
  const [loading,setLoading]=useState(false);
  const [proteinLoading,setProteinLoading]=useState(false);
  const [refresh,setRefresh]=useState(0);
  const known=useMemo(()=>data?.compounds||[],[data]);
  const names=useMemo(()=>new Map(known.map(c=>[c.cid,c])),[known]);
  const proteinGenes=useMemo(()=>GENE_CANDIDATES.filter(g=>data?.proteins.some(p=>p.name===g)),[data]);

  useEffect(()=>{ if(!data)return;let active=true;
    async function fetchBatch(){
      setLoading(true);setError("");
      const shuffled=[...known].sort(()=>Math.random()-.5).slice(0,3);
      // All identifiers come from the real DAVIS reference. Metadata comes live from PubChem.
      const outcomes=await Promise.allSettled(shuffled.map(c=>loadPubChem(c.cid)));
      if(!active)return;
      const items=outcomes.flatMap((o,i)=>o.status==="fulfilled"?[{...o.value,smiles:shuffled[i].smiles}]:[]);
      setCompounds(items);
      if(outcomes.some(x=>x.status==="rejected"))setError("Some PubChem requests could not be completed; only verified live results are shown.");
      if(!items.length)setError("PubChem could not be reached. Open a source link or try refreshing.");
      setLoading(false);
    }
    void fetchBatch();return()=>{active=false;};
  },[data,known,refresh]);

  useEffect(()=>{if(!data || !proteinGenes.length)return;let active=true;
    async function fetchProteins(){
      setProteinLoading(true);setProteinError("");
      const genes=[...proteinGenes].sort(()=>Math.random()-.5).slice(0,2);
      const outcomes=await Promise.allSettled(genes.map(uniprot));
      if(!active)return;
      setProteins(outcomes.flatMap(o=>o.status==="fulfilled"?[o.value]:[]));
      if(outcomes.some(o=>o.status==="rejected"))setProteinError("Some UniProt entries could not be retrieved; only verified records are shown.");
      setProteinLoading(false);
    }
    void fetchProteins();return()=>{active=false;};
  },[data,proteinGenes,refresh]);

  const shown=compounds.filter(c=>(c.name+" "+c.cid+" "+c.molecularFormula).toLowerCase().includes(search.toLowerCase()));
  return <div className="proto-content">
    <PageTitle eyebrow="02 / EXPLORE SOURCES" title="Explore"
      description="Discover real chemical compounds and reviewed protein entries from public scientific databases, with source links for every record."
      actions={<button className="proto-button proto-button-secondary" type="button" onClick={()=>setRefresh(n=>n+1)} disabled={!data||loading||proteinLoading}>
        <Symbol name="reload" size={16}/> Discover another set</button>}/>
    <div className="proto-explore-source"><span className="proto-live-indicator"/> LIVE DATABASE QUERIES <span>PubChem PUG REST + UniProt REST. Each entry comes from a real external record; no synthetic articles or experimental measurements.</span></div>
    <section className="proto-explore-group">
      <div className="proto-explore-heading"><div><span className="proto-section-number">01</span><h2>Compounds from PubChem</h2><InfoTip label="Discovery pool">Compound IDs are drawn at random from the existing DAVIS reference. PubChem supplies current compound names and molecular metadata; these cards are not new screening results.</InfoTip></div>
        <input aria-label="Filter discovered compounds" placeholder="Filter by name or CID…" value={search} onChange={e=>setSearch(e.target.value)}/></div>
      {loading ? <div className="proto-loading-state">Fetching live compound metadata from PubChem…</div>
        : shown.length ? <div className="proto-explore-grid">{shown.map(item=><article className="proto-source-card" key={item.cid}>
          <div className="proto-source-top"><span>COMPOUND / CID {item.cid}</span><span className="proto-source-chip">PUBCHEM</span></div>
          <h3>{item.name}</h3><p className="proto-source-formula">{item.molecularFormula||"Formula unavailable"}</p>
          <div className="proto-source-detail"><span>Molecular weight</span><strong>{item.molecularWeight ? item.molecularWeight+" g/mol":"Not reported"}</strong></div>
          <div className="proto-source-actions"><button type="button" className="proto-inline-action" onClick={()=>{const c=names.get(item.cid);if(c)onUseCompound(c);}}>Use SMILES <Symbol name="arrow" size={14}/></button>
            <a href={item.url} target="_blank" rel="noreferrer">PubChem record <Symbol name="external" size={14}/></a></div>
        </article>)}</div> : <EmptyMessage title={data?"No live compounds available":"Loading reference data"} description={data?"Refresh to fetch verified source records; no fabricated fallbacks are displayed.":"Reading the local DAVIS compound identifiers."}/>}
      {error&&<p className="proto-muted-note" role="status">{error}</p>}
    </section>
    <section className="proto-explore-group">
      <div className="proto-explore-heading"><div><span className="proto-section-number">02</span><h2>Reviewed proteins from UniProt</h2><InfoTip label="Protein sources">Reviewed human canonical protein entries are retrieved by exact gene name from UniProt, not inferred from a SMILES or generated sequence. Mutant DAVIS sequences are not claimed to be identical.</InfoTip></div></div>
      {proteinLoading ? <div className="proto-loading-state">Querying reviewed human protein records…</div>
        : proteins.length ? <div className="proto-explore-grid">{proteins.map(item=><article className="proto-source-card protein" key={item.accession}>
          <div className="proto-source-top"><span>PROTEIN / {item.accession}</span><span className="proto-source-chip">UNIPROT</span></div>
          <h3>{item.gene}</h3><p className="proto-protein-fullname">{item.name}</p>
          <div className="proto-source-detail"><span>Canonical sequence length</span><strong>{item.length.toLocaleString()} aa</strong></div>
          <div className="proto-source-actions"><a href={item.url} target="_blank" rel="noreferrer">Reviewed UniProt record <Symbol name="external" size={14}/></a>
            <a href={`https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(item.gene)}`} target="_blank" rel="noreferrer">Find literature <Symbol name="external" size={14}/></a></div>
        </article>)}</div>
        : <EmptyMessage title="No live protein records" description="The UniProt service may be unreachable. Try another discovery set; no identity is assumed without a matched record."/>}
      {proteinError&&<p className="proto-muted-note" role="status">{proteinError}</p>}
    </section>
    <footer className="proto-explore-disclaimer">Source records are shown for reference and exploration, not as proof of binding or as GeoFuse predictions. A verified bound complex is still required for native 3D inference.</footer>
  </div>;
}
