import { useEffect, useMemo, useRef, useState } from "react";
import { Map as MapaML, NavigationControl, Popup, type MapLayerMouseEvent } from "./maplibre";
import type { FeatureCollection } from "geojson";
import { cargar, formatear, formatearCorto } from "../datos";

// Escala secuencial de un solo tono (azul), de claro a oscuro: 5 clases por cuantiles.
const RAMPA = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
const SIN_DATO = "#d9d8d4";
export const ESTILO_PLANO = "https://tiles.openfreemap.org/styles/positron";
// Límites del municipio (lon, lat): el mapa arranca encuadrado en los 96 distritos.
export const LIMITES_SP: [[number, number], [number, number]] = [[-46.83, -24.01], [-46.36, -23.36]];

interface Props {
  valores: Record<string, number | null>;
  unidad: string;
  seleccionado: string | null;
  onSeleccionar: (codigo: string) => void;
}

// Cortes por cuantiles sin repetir: si muchos distritos tienen el mismo valor (p. ej. 100 %
// de cobertura), quedan menos clases y la leyenda no muestra dos veces el mismo límite.
function cortesCuantiles(valores: number[], clases = RAMPA.length): number[] {
  const orden = [...valores].sort((a, b) => a - b);
  const cortes = Array.from({ length: clases - 1 }, (_, i) => orden[Math.floor(((i + 1) * orden.length) / clases)]);
  return [...new Set(cortes)].filter((c) => c > orden[0]);
}

// Con menos clases, los colores se reparten a lo largo de toda la rampa.
function colorDeClase(clase: number, totalClases: number): string {
  if (totalClases <= 1) return RAMPA[RAMPA.length - 1];
  return RAMPA[Math.round((clase * (RAMPA.length - 1)) / (totalClases - 1))];
}

export default function MapaDistritos({ valores, unidad, seleccionado, onSeleccionar }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaML | null>(null);
  const [listo, setListo] = useState(false);
  const alSeleccionar = useRef(onSeleccionar);
  alSeleccionar.current = onSeleccionar;
  const unidadRef = useRef(unidad);
  unidadRef.current = unidad;
  const valoresRef = useRef(valores);
  valoresRef.current = valores;

  const cortes = useMemo(
    () => cortesCuantiles(Object.values(valores).filter((v): v is number => v !== null)),
    [valores],
  );

  useEffect(() => {
    const m = new MapaML({
      container: contenedor.current!,
      style: ESTILO_PLANO,
      bounds: LIMITES_SP,
      fitBoundsOptions: { padding: 12 },
      minZoom: 8,
      attributionControl: { compact: true },
    });
    mapa.current = m;
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8 });

    m.on("load", async () => {
      const geo = await cargar<FeatureCollection>("territorio/distritos.geojson");
      m.addSource("distritos", { type: "geojson", data: geo, promoteId: "codigo_distrito" });
      m.addLayer({
        id: "distritos-relleno",
        type: "fill",
        source: "distritos",
        paint: { "fill-color": ["coalesce", ["feature-state", "color"], SIN_DATO], "fill-opacity": 0.85 },
      });
      m.addLayer({
        id: "distritos-borde",
        type: "line",
        source: "distritos",
        paint: { "line-color": "#ffffff", "line-width": 0.8 },
      });
      m.addLayer({
        id: "distritos-seleccion",
        type: "line",
        source: "distritos",
        paint: {
          "line-color": "#0b0b0b",
          "line-width": ["case", ["boolean", ["feature-state", "seleccionado"], false], 2.5, 0],
        },
      });
      setListo(true);

      m.on("mousemove", "distritos-relleno", (e: MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (!f) return;
        m.getCanvas().style.cursor = "pointer";
        const codigo = f.properties.codigo_distrito as string;
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<strong>${f.properties.nombre_visible}</strong><br>${formatear(valoresRef.current[codigo] ?? null, unidadRef.current)} <span class="popup-unidad">${unidadRef.current.toLowerCase()}</span>`,
          )
          .addTo(m);
      });
      m.on("mouseleave", "distritos-relleno", () => {
        m.getCanvas().style.cursor = "";
        popup.remove();
      });
      m.on("click", "distritos-relleno", (e: MapLayerMouseEvent) => {
        const codigo = e.features?.[0]?.properties.codigo_distrito;
        if (codigo) alSeleccionar.current(codigo as string);
      });
    });
    return () => {
      setListo(false);
      m.remove();
    };
  }, []);

  // Pinta valores y selección cada vez que cambian.
  useEffect(() => {
    const m = mapa.current;
    if (!m || !listo) return;
    for (const [codigo, valor] of Object.entries(valores)) {
      const clase = valor === null ? -1 : cortes.filter((c) => valor >= c).length;
      m.setFeatureState(
        { source: "distritos", id: codigo },
        { color: clase < 0 ? SIN_DATO : colorDeClase(clase, cortes.length + 1), seleccionado: codigo === seleccionado },
      );
    }
  }, [valores, cortes, seleccionado, listo]);

  const limites = [Math.min(...Object.values(valores).filter((v): v is number => v !== null)), ...cortes];

  return (
    <figure className="mapa-figura">
      <div ref={contenedor} className="mapa" role="img" aria-label={`Mapa coroplético de distritos: ${unidad}`} />
      <figcaption className="leyenda">
        <span className="leyenda-titulo">{unidad} (cuantiles)</span>
        <ol>
          {limites.map((limite, i) => (
            <li key={i}>
              <span className="muestra" style={{ background: colorDeClase(i, limites.length) }} />
              {Number.isFinite(limite) ? `${formatearCorto(limite)}+` : ""}
            </li>
          ))}
        </ol>
      </figcaption>
    </figure>
  );
}
