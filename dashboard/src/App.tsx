import { useEffect, useState } from "react";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { api, type Alert, type Hotspot, type InpeRiskDay, type OverviewNode } from "./api";

// Live updates come over SSE (/api/stream). Polling is only a safety net if the stream drops.
const FALLBACK_POLL_MS = 60_000;
const DEBOUNCE_MS = 400;
const BRAZIL_CENTER: [number, number] = [-14.2, -51.9];

type NodeState = OverviewNode;

function scoreColor(score = 0) {
  if (score >= 0.6) return "#d7263d";
  if (score >= 0.3) return "#f49d37";
  return "#2e9e5b";
}

const DANGER_COLORS: Record<string, string> = {
  nula: "#2e9e5b", pequena: "#8bbf3f", media: "#f2c230", alta: "#f49d37", muito_alta: "#d7263d",
};
const DANGER_LABEL: Record<string, string> = {
  nula: "Nula", pequena: "Pequena", media: "Média", alta: "Alta", muito_alta: "Muito alta",
};

// INPE Risco de Fogo classes use the same 5-step palette as FMA+.
const RF_COLORS: Record<string, string> = {
  minimo: "#2e9e5b", baixo: "#8bbf3f", medio: "#f2c230", alto: "#f49d37", critico: "#d7263d",
};

// The official INPE risk drives the area color; FMA+ is the fallback when INPE has no data yet.
function siteColor(n: NodeState) {
  if (n.inpe?.today) return RF_COLORS[n.inpe.today.risk_class];
  return DANGER_COLORS[n.danger?.danger_class ?? ""] ?? "#888";
}

function dayLabel(d: InpeRiskDay) {
  const [, m, day] = d.date.split("-");
  return `${day}/${m}`;
}

function fmt(ts: string) {
  return new Date(ts).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export default function App() {
  const [nodes, setNodes] = useState<NodeState[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [live, setLive] = useState(false);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const [ns, hs, as] = await Promise.all([api.overview(), api.hotspots(), api.alerts()]);
        if (!alive) return;
        setNodes(ns);
        setHotspots(hs);
        setAlerts(as);
        setError(null);
      } catch (e) {
        if (alive) setError(String(e));
      }
    }
    const scheduleLoad = () => {
      clearTimeout(timer);
      timer = setTimeout(load, DEBOUNCE_MS);
    };

    load();
    const es = new EventSource("/api/stream");
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false); // EventSource reconnects by itself
    for (const ev of ["alert", "reading", "refresh"]) es.addEventListener(ev, scheduleLoad);
    const poll = setInterval(load, FALLBACK_POLL_MS);

    return () => {
      alive = false;
      clearTimeout(timer);
      clearInterval(poll);
      es.close();
    };
  }, []);

  return (
    <div className="layout">
      <header>
        <h1>🔥 Sentinela do Fogo</h1>
        <span className="meta">
          {nodes.filter((n) => n.kind === "virtual").length} áreas monitoradas ·{" "}
          {nodes.filter((n) => n.kind !== "virtual").length} sensores · {hotspots.length} focos INPE (24h)
          {" · "}<span className={live ? "live" : "offline"}>{live ? "● ao vivo" : "○ reconectando"}</span>
          {error && <span className="error"> · erro: {error}</span>}
        </span>
      </header>
      <MapContainer center={BRAZIL_CENTER} zoom={4} className="map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {hotspots.map((h, i) => (
          <CircleMarker key={`h${i}`} center={[h.lat, h.lon]} radius={2}
            pathOptions={{ color: "#ff5a00", weight: 0, fillOpacity: 0.6 }}>
            <Popup>Foco {h.satellite}<br />{fmt(h.ts)}</Popup>
          </CircleMarker>
        ))}
        {nodes.filter((n) => n.kind === "virtual").map((n) => {
          const color = siteColor(n);
          return (
            <Circle key={n.id} center={[n.lat, n.lon]} radius={(n.radius_km ?? 10) * 1000}
              pathOptions={{ color, weight: 2, fillColor: color, fillOpacity: 0.15 }}>
              <Popup>
                <strong>{n.name ?? n.id}</strong> ({n.biome})<br />
                {n.inpe?.today && <>Risco INPE hoje: <strong>{n.inpe.today.label}</strong> ({n.inpe.today.rf.toFixed(2)})<br /></>}
                {n.inpe && n.inpe.forecast.length > 0 && (
                  <>Previsão: {n.inpe.forecast.map((d) => `${dayLabel(d)} ${d.label}`).join(" · ")}<br /></>
                )}
                FMA+: <strong>{DANGER_LABEL[n.danger?.danger_class ?? ""] ?? "-"}</strong>
                {n.danger && <> ({n.danger.fma_plus}, {n.danger.days_used} dias)</>}<br />
                {n.last && <>{n.last.temp_c.toFixed(1)}°C · UR {n.last.humidity_pct.toFixed(0)}% · vento {n.last.wind_ms?.toFixed(1) ?? "-"} m/s<br /></>}
                raio monitorado: {n.radius_km} km · atualizado: {n.last_seen ? fmt(n.last_seen) : "-"}
              </Popup>
            </Circle>
          );
        })}
        {nodes.filter((n) => n.kind !== "virtual").map((n) => (
          <CircleMarker key={n.id} center={[n.lat, n.lon]} radius={9}
            pathOptions={{ color: "#111", weight: 2, fillColor: scoreColor(n.last?.score), fillOpacity: 0.9 }}>
            <Popup>
              <strong>{n.id}</strong><br />
              {n.last && (
                <>
                  {n.last.temp_c.toFixed(1)}°C · UR {n.last.humidity_pct.toFixed(0)}% · fumaça {n.last.smoke_ppm?.toFixed(0) ?? "-"} ppm<br />
                  score detecção: {n.last.score.toFixed(2)}{n.last.flame && " · 🔥 chama"}<br />
                </>
              )}
              {n.danger && <>FMA+ {n.danger.fma_plus} ({n.danger.danger_class})<br /></>}
              bateria: {n.battery_v?.toFixed(2) ?? "-"} V<br />
              visto: {n.last_seen ? fmt(n.last_seen) : "-"}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <aside>
        <h2>Áreas monitoradas</h2>
        <ul className="sites">
          {nodes.filter((n) => n.kind === "virtual").map((n) => (
            <li key={n.id} className="site">
              <div className="site-head">
                <span className="dot" style={{ background: siteColor(n) }} />
                {n.name ?? n.id}
              </div>
              <div className="meta">
                {n.inpe?.today
                  ? <>INPE hoje: <strong>{n.inpe.today.label}</strong> ({n.inpe.today.rf.toFixed(2)})</>
                  : "INPE: sem dados"}
                {" · "}FMA+ {DANGER_LABEL[n.danger?.danger_class ?? ""] ?? "-"}
                {n.danger && ` (${n.danger.fma_plus})`}
              </div>
              {n.inpe && n.inpe.forecast.length > 0 && (
                <div className="forecast">
                  {n.inpe.forecast.map((d) => (
                    <span key={d.date} className="chip" title={`RF ${d.rf.toFixed(2)} (máx. ${d.rf_max.toFixed(2)})`}
                      style={{ borderColor: RF_COLORS[d.risk_class] }}>
                      <span className="dot" style={{ background: RF_COLORS[d.risk_class] }} />
                      {dayLabel(d)} {d.label}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
        <h2>Alertas</h2>
        {alerts.length === 0 && <p className="meta">Nenhum alerta.</p>}
        <ul>
          {alerts.map((a) => (
            <li key={a.id}>
              <div className="meta">{fmt(a.ts)} · {a.delivered ? "enviado" : "não enviado"}</div>
              {a.message}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
