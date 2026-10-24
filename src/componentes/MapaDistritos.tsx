import type { FeatureCollection } from "geojson";
import { useEffect, useMemo, useRef, useState } from "react";
import { cargar, formatear, formatearCorto } from "../datos";
import { type Tema, useTema } from "../tema";
import { agregarMascara, estiloSaoPaulo, LIMITES_NAVEGACION, LIMITES_SP } from "./mapaBase";
import { Map as MapaML, type MapLayerMouseEvent, NavigationControl, Popup } from "./maplibre";

// Escala secuencial de un solo tono (azul) en 5 clases por cuantiles. El valor alto es siempre el
// de más contraste con el fondo: en claro va de claro a oscuro y en oscuro al revés.
const RAMPA_CLARA = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];

const COLORES: Record<Tema, { rampa: string[]; sinDato: string; borde: string; seleccion: string }> = {
  claro: { rampa: RAMPA_CLARA, sinDato: "#d9d8d4", borde: "#ffffff", seleccion: "#0b0b0b" },
  oscuro: { rampa: [...RAMPA_CLARA].reverse(), sinDato: "#3a3a37", borde: "#121211", seleccion: "#ffffff" },
};

const NUMERO_CLASES = RAMPA_CLARA.length;

interface Props {
  valores: Record<string, number | null>;
  unidad: string;
  seleccionado: string | null;
  onSeleccionar: (codigo: string) => void;
}

// Cortes por cuantiles sin repetir: si muchos distritos tienen el mismo valor (p. ej. 100 %
// de cobertura), quedan menos clases y la leyenda no muestra dos veces el mismo límite.
function cortesCuantiles(valores: number[]): number[] {
  const orden = [...valores].sort((a, b) => a - b);
  const cortes = Array.from(
    { length: NUMERO_CLASES - 1 },
    (_, i) => orden[Math.floor(((i + 1) * orden.length) / NUMERO_CLASES)],
  );
  return [...new Set(cortes)].filter((c) => c > orden[0]);
}

// Con menos clases, los colores se reparten a lo largo de toda la rampa.
function colorDeClase(rampa: string[], clase: number, totalClases: number): string {
  if (totalClases <= 1) return rampa[rampa.length - 1];
  return rampa[Math.round((clase * (rampa.length - 1)) / (totalClases - 1))];
}

export default function MapaDistritos({ valores, unidad, seleccionado, onSeleccionar }: Props) {
  const tema = useTema();
  const colores = COLORES[tema];
  const contenedor = useRef<HTMLDivElement>(null);
  const [mapa, setMapa] = useState<MapaML | null>(null);

  // Los manejadores del mapa se registran una vez; leen siempre los últimos valores por aquí.
  const actual = useRef({ valores, unidad, onSeleccionar });
  actual.current = { valores, unidad, onSeleccionar };

  const cortes = useMemo(
    () => cortesCuantiles(Object.values(valores).filter((v): v is number => v !== null)),
    [valores],
  );

  // Crea el mapa (y lo recrea con el otro estilo al cambiar de tema).
  useEffect(() => {
    let creado: MapaML | null = null;
    let cancelado = false;
    const { sinDato, borde, seleccion } = COLORES[tema];

    estiloSaoPaulo("plano", tema).then((estilo) => {
      if (cancelado) return;
      const m = new MapaML({
        container: contenedor.current!,
        style: estilo,
        bounds: LIMITES_SP,
        fitBoundsOptions: { padding: 12 },
        maxBounds: LIMITES_NAVEGACION,
        attributionControl: { compact: true },
      });
      creado = m;
      m.addControl(new NavigationControl({ showCompass: false }), "top-right");

      m.on("load", async () => {
        await agregarMascara(m, seleccion);
        const geo = await cargar<FeatureCollection>("territorio/distritos.geojson");
        m.addSource("distritos", { type: "geojson", data: geo, promoteId: "codigo_distrito" });
        m.addLayer({
          id: "distritos-relleno",
          type: "fill",
          source: "distritos",
          paint: { "fill-color": ["coalesce", ["feature-state", "color"], sinDato], "fill-opacity": 0.85 },
        });
        m.addLayer({
          id: "distritos-borde",
          type: "line",
          source: "distritos",
          paint: { "line-color": borde, "line-width": 0.8 },
        });
        m.addLayer({
          id: "distritos-seleccion",
          type: "line",
          source: "distritos",
          paint: {
            "line-color": seleccion,
            "line-width": ["case", ["boolean", ["feature-state", "seleccionado"], false], 2.5, 0],
          },
        });
        registrarEventos(m);
        setMapa(m);
      });
    });

    function registrarEventos(m: MapaML) {
      const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8 });
      m.on("mousemove", "distritos-relleno", (e: MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (!f) return;
        const { valores, unidad } = actual.current;
        const codigo = f.properties.codigo_distrito as string;
        m.getCanvas().style.cursor = "pointer";
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<strong>${f.properties.nombre_visible}</strong><br>${formatear(valores[codigo] ?? null, unidad)} <span class="popup-unidad">${unidad.toLowerCase()}</span>`,
          )
          .addTo(m);
      });
      m.on("mouseleave", "distritos-relleno", () => {
        m.getCanvas().style.cursor = "";
        popup.remove();
      });
      m.on("click", "distritos-relleno", (e: MapLayerMouseEvent) => {
        const codigo = e.features?.[0]?.properties.codigo_distrito;
        if (codigo) actual.current.onSeleccionar(codigo as string);
      });
    }

    return () => {
      cancelado = true;
      setMapa(null);
      creado?.remove();
    };
  }, [tema]);

  // Pinta valores y selección cada vez que cambian.
  useEffect(() => {
    if (!mapa) return;
    for (const [codigo, valor] of Object.entries(valores)) {
      const clase = valor === null ? -1 : cortes.filter((c) => valor >= c).length;
      const color = clase < 0 ? colores.sinDato : colorDeClase(colores.rampa, clase, cortes.length + 1);
      mapa.setFeatureState({ source: "distritos", id: codigo }, { color, seleccionado: codigo === seleccionado });
    }
  }, [mapa, valores, cortes, seleccionado, colores]);

  const minimo = Math.min(...Object.values(valores).filter((v): v is number => v !== null));
  const limites = [minimo, ...cortes];

  return (
    <figure className="mapa-figura">
      <div className="mapa-contenedor">
        <div ref={contenedor} className="mapa" role="img" aria-label={`Mapa coroplético de distritos: ${unidad}`} />
        {!mapa && <p className="mapa-cargando">Cargando mapa…</p>}
      </div>
      <figcaption className="leyenda">
        <span className="leyenda-titulo">{unidad} (cuantiles)</span>
        <ol>
          {limites.map((limite, i) => (
            <li key={limite}>
              <span className="muestra" style={{ background: colorDeClase(colores.rampa, i, limites.length) }} />
              {Number.isFinite(limite) ? `${formatearCorto(limite)}+` : ""}
            </li>
          ))}
        </ol>
      </figcaption>
    </figure>
  );
}
