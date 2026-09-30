// Maps a `projects_merged_conf1` / `projects_draft` row to the GeoJSON feature the
// public map reads. Emits only the shapefile-style keys (the same 16 as the hosted
// file before the admin dashboard). The map and search read these first and only
// fall back to SCALE-R CSV keys (Project_Name, …), so writing both would double
// the file size and its parse time for no visible change.

export const PROJECT_COLUMNS = [
  'id',
  'project_na',
  'name',
  'city',
  'latitude',
  'longitude',
  'infrastruc',
  'categories',
  'disaster_f',
  'new_15_25_',
  'project_st',
  'project_en',
  'project_status',
  'status_category',
  'estimated_cost',
  'implementa',
  'link_to_da',
  'additional',
  'tract_geoid',
] as const;

export const PROJECT_SELECT = PROJECT_COLUMNS.join(', ');

export type ProjectRow = Partial<Record<(typeof PROJECT_COLUMNS)[number], string | number | null>>;

const INFRA_CANONICAL: Record<string, string> = {
  blue: 'Blue Infrastructure',
  'blue infrastructure': 'Blue Infrastructure',
  green: 'Green Infrastructure',
  'green infrastructure': 'Green Infrastructure',
  grey: 'Gray Infrastructure',
  'grey infrastructure': 'Gray Infrastructure',
  gray: 'Gray Infrastructure',
  'gray infrastructure': 'Gray Infrastructure',
  hybrid: 'Hybrid',
};

export function normalizeInfrastruc(value: unknown): string {
  if (!value) return '';
  const text = String(value);
  return INFRA_CANONICAL[text.trim().toLowerCase()] ?? text;
}

function str(value: unknown): string {
  return value == null ? '' : String(value);
}

export function projectToFeature(row: ProjectRow) {
  const lat = Number(row.latitude);
  const lng = Number(row.longitude);
  if (row.latitude == null || row.longitude == null) return null;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

  const projectName = str(row.project_na);
  const city = str(row.city || row.name || '');
  const infra = normalizeInfrastruc(row.infrastruc);
  const hazard = str(row.disaster_f);
  const description = str(row.new_15_25_);
  const status = str(row.project_status);
  const cost = row.estimated_cost != null ? String(row.estimated_cost) : '';
  const source = str(row.link_to_da);
  const projectId = str(row.implementa);
  const spatial = str(row.additional ?? row.categories ?? '');
  const reportedYear = str(row.project_st);

  return {
    type: 'Feature' as const,
    id: row.id ?? undefined,
    geometry: { type: 'Point' as const, coordinates: [lng, lat] },
    properties: {
      Project_Na: projectName,
      NAME: city,
      City: city,
      Infrastruc: infra,
      Categories: spatial,
      Disaster_F: hazard,
      New_15_25_: description,
      Project_St: reportedYear,
      Project_En: str(row.project_en),
      Project__1: status,
      Status_Category: str(row.status_category),
      Estimated_: cost,
      Implementa: projectId,
      Link_to_Da: source,
      Additional: spatial,
      TRACT_GEOID: str(row.tract_geoid),
    },
  };
}

export function projectsToFeatureCollection(rows: ProjectRow[]) {
  const features = [];
  for (const row of rows) {
    const feature = projectToFeature(row);
    if (feature) features.push(feature);
  }
  return { type: 'FeatureCollection' as const, features };
}
