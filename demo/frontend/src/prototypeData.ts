import type { GlossaryDataset } from "./glossaryData";

export type ModelPrediction = {
  status: "ok";
  prediction_pKd: number;
  calibrated_2d_pKd: number;
  sample_id: string;
  geometry_used: boolean;
  geometry_source?: string;
};
export type VerifiedExample = { sample_id: string; smiles: string; sequence: string; source: string };
export type SavedRun = {
  id: string;
  type: "prediction" | "comparison";
  name: string;
  timestamp: string;
  compoundA: string;
  compoundB?: string;
  protein: string;
  resultA: number;
  resultB?: number;
  sampleA: string;
  sampleB?: string;
  notes: string;
  favorite: boolean;
};
export type DiscoveryItem = {
  cid: string;
  name: string;
  smiles: string;
  molecularFormula?: string;
  molecularWeight?: string;
  source: "PubChem";
  url: string;
};
const HISTORY_KEY = "geofuse-cpi:notebook:v1";

export function cleanSequence(raw: string): string {
  return raw.split(/\r?\n/).filter(line => !line.trimStart().startsWith(">"))
    .join("").replace(/\s+/g, "").toUpperCase();
}
export function validatePair(smiles: string, protein: string): string | null {
  if (!smiles.trim()) return "Enter a compound SMILES.";
  if (smiles.trim().length > 500) return "SMILES exceeds the model's 500-character limit.";
  const sequence = cleanSequence(protein);
  if (!sequence || sequence.length > 2048 || !/^[ACDEFGHIKLMNPQRSTVWYX]+$/.test(sequence))
    return "Enter 1–2048 standard amino-acid characters (FASTA accepted).";
  return null;
}
export async function requestJson<T>(url: string, body?: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new Error("The service could not be reached. Confirm the local server is running.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error((data as { error?: string } | null)?.error || `Service returned HTTP ${response.status}.`);
  return data as T;
}
export async function predict(smiles: string, sequence: string): Promise<ModelPrediction> {
  const result = await requestJson<ModelPrediction>("/api/geocpi/predict", { smiles: smiles.trim(), sequence: cleanSequence(sequence) });
  if (result.status !== "ok" || result.geometry_used !== true || !Number.isFinite(result.prediction_pKd))
    throw new Error("The backend did not provide a verified fused prediction.");
  return result;
}
export function loadSavedRuns(): SavedRun[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const rows: unknown = JSON.parse(raw);
    if (!Array.isArray(rows)) return [];
    return rows.filter((item): item is SavedRun => !!item && typeof item === "object"
      && typeof item.id === "string" && (item.type === "prediction" || item.type === "comparison")
      && typeof item.name === "string" && typeof item.resultA === "number").slice(0, 500);
  } catch { return []; }
}
export function saveRuns(runs: SavedRun[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(runs.slice(0, 500)));
}
export function newId() { return crypto.randomUUID(); }
export function identifyCompound(data: GlossaryDataset | null, smiles: string) {
  return data?.compounds.find(c => c.smiles === smiles.trim());
}
export function identifyProtein(data: GlossaryDataset | null, seq: string) {
  return data?.proteins.find(p => p.sequence === cleanSequence(seq));
}
export function formatPKd(value: number): string {
  return value.toFixed(3);
}
export async function loadPubChem(cid: string): Promise<DiscoveryItem> {
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${encodeURIComponent(cid)}/property/Title,MolecularFormula,MolecularWeight/JSON`;
  let response: Response;
  try { response = await fetch(url); }
  catch { throw new Error("PubChem could not be reached from this browser."); }
  if (!response.ok) throw new Error(`PubChem returned HTTP ${response.status}.`);
  const data = await response.json() as { PropertyTable?: { Properties?: Array<{ CID: number; Title?: string; MolecularFormula?: string; MolecularWeight?: string }> } };
  const row = data.PropertyTable?.Properties?.[0];
  if (!row || String(row.CID) !== cid) throw new Error("PubChem returned an unexpected compound.");
  return { cid, name: row.Title || `CID ${cid}`, smiles: "", molecularFormula: row.MolecularFormula,
    molecularWeight: row.MolecularWeight, source: "PubChem", url: `https://pubchem.ncbi.nlm.nih.gov/compound/${cid}` };
}
export function exportJson(filename: string, value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 30000);
}
