export type Node = {
  id: string; name: string | null; lat: number; lon: number;
  biome: string | null; kind: string; radius_km: number | null; last_seen: string | null; battery_v: number | null;
};
export type Hotspot = { lat: number; lon: number; satellite: string; ts: string };
export type Alert = { id: number; node_id: string; ts: string; kind: string; score: number; message: string; delivered: boolean };
export type Reading = { ts: string; temp_c: number; humidity_pct: number; wind_ms: number | null; smoke_ppm: number | null; flame: boolean; score: number };
export type Danger = { node_id: string; fma_plus: number; danger_class: string; days_used: number };

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export type OverviewNode = Node & { last: Reading | null; danger: Danger | null };

export const api = {
  overview: () => get<OverviewNode[]>("/api/overview"),
  nodes: () => get<Node[]>("/api/nodes"),
  hotspots: (hours = 24) => get<Hotspot[]>(`/api/hotspots?hours=${hours}`),
  alerts: () => get<Alert[]>("/api/alerts?limit=20"),
  readings: (id: string) => get<Reading[]>(`/api/nodes/${encodeURIComponent(id)}/readings?limit=1`),
  danger: (id: string) => get<Danger>(`/api/nodes/${encodeURIComponent(id)}/danger`),
};
