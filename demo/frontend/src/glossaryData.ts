export type GlossaryCompound = {
  cid: string;
  name: string;
  smiles: string;
};

export type GlossaryProtein = {
  name: string;
  sequence: string;
};

export type GlossaryDataset = {
  source: string;
  sourceUrl: string;
  compoundNameSource: string;
  affinityUnit: string;
  censoringNote: string;
  compounds: GlossaryCompound[];
  proteins: GlossaryProtein[];
  kdNm: number[][];
};

let cached: Promise<GlossaryDataset> | null = null;

export function loadGlossary(): Promise<GlossaryDataset> {
  if (!cached) {
    cached = fetch("/davis-glossary.json").then(async response => {
      if (!response.ok) throw new Error("Could not load DAVIS reference data.");
      const data = await response.json() as GlossaryDataset;
      if (!data.compounds?.length || !data.proteins?.length
          || data.kdNm.length !== data.compounds.length
          || data.kdNm.some(row => row.length !== data.proteins.length)) {
        throw new Error("DAVIS reference file is incomplete.");
      }
      return data;
    }).catch(error => {
      cached = null;
      throw error;
    });
  }
  return cached;
}
