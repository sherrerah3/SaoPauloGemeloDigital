// Mapas base de OpenFreeMap recortados a São Paulo.
//
// El estilo original apunta a las teselas de todo el planeta. Aquí se reescribe para que:
// 1. la fuente vectorial declare `bounds` y MapLibre no pida teselas fuera de la ciudad;
// 2. no se cargue el relieve mundial de Natural Earth (solo se ve en zooms bajos);
// 3. una máscara tape lo que queda fuera del municipio (territorio/municipio.geojson).

import type { FeatureCollection } from "geojson";
import { cargar } from "../datos";
import type { Tema } from "../tema";
import type { LayerSpecification, Map as MapaML, SourceSpecification, StyleSpecification } from "./maplibre";

type LngLat = [number, number];

/** Rectángulo de los 96 distritos (oeste-sur, este-norte). */
export const LIMITES_SP: [LngLat, LngLat] = [
  [-46.83, -24.01],
  [-46.36, -23.36],
];

/** Hasta dónde se puede mover la cámara: el municipio y un margen. */
export const LIMITES_NAVEGACION: [LngLat, LngLat] = [
  [-47.25, -24.35],
  [-45.95, -23.0],
];

const BASE_OPENFREEMAP = "https://tiles.openfreemap.org/styles";

const ESTILOS: Record<"plano" | "3d", Record<Tema, string>> = {
  plano: { claro: "positron", oscuro: "dark" },
  "3d": { claro: "liberty", oscuro: "dark" },
};

// El estilo oscuro no trae edificios 3D: se agregan con la misma regla que Liberty.
const EDIFICIOS_3D_OSCURO: LayerSpecification = {
  id: "building-3d",
  type: "fill-extrusion",
  source: "openmaptiles",
  "source-layer": "building",
  minzoom: 14,
  paint: {
    "fill-extrusion-base": ["get", "render_min_height"],
    "fill-extrusion-color": "hsl(220, 6%, 22%)",
    "fill-extrusion-height": ["get", "render_height"],
    "fill-extrusion-opacity": 0.85,
  },
};

interface TileJSON {
  tiles: string[];
  minzoom?: number;
  maxzoom?: number;
  attribution?: string;
}

const cache = new Map<string, Promise<StyleSpecification>>();

/** Estilo de OpenFreeMap listo para usar, limitado a São Paulo. */
export function estiloSaoPaulo(tipo: "plano" | "3d", tema: Tema): Promise<StyleSpecification> {
  const nombre = ESTILOS[tipo][tema];
  const clave = `${nombre}-${tipo}`;
  if (!cache.has(clave)) cache.set(clave, construirEstilo(nombre, tipo === "3d"));
  return cache.get(clave)!;
}

async function construirEstilo(nombre: string, edificios3d: boolean): Promise<StyleSpecification> {
  const estilo: StyleSpecification = await leerJSON(`${BASE_OPENFREEMAP}/${nombre}`);
  const sources: Record<string, SourceSpecification> = {};

  for (const [id, fuente] of Object.entries(estilo.sources)) {
    if (fuente.type === "raster") continue; // relieve mundial de Natural Earth
    if (fuente.type === "vector" && fuente.url) {
      const tilejson: TileJSON = await leerJSON(fuente.url);
      sources[id] = {
        type: "vector",
        tiles: tilejson.tiles,
        minzoom: tilejson.minzoom,
        maxzoom: tilejson.maxzoom,
        attribution: tilejson.attribution,
        bounds: [...LIMITES_NAVEGACION[0], ...LIMITES_NAVEGACION[1]],
      };
    } else {
      sources[id] = fuente;
    }
  }

  const layers = estilo.layers.filter((capa) => !("source" in capa) || capa.source in sources);
  if (edificios3d && !layers.some((capa) => capa.type === "fill-extrusion")) layers.push(EDIFICIOS_3D_OSCURO);

  return { ...estilo, sources, layers };
}

async function leerJSON<T>(url: string): Promise<T> {
  const respuesta = await fetch(url);
  if (!respuesta.ok) throw new Error(`No se pudo leer ${url} (${respuesta.status})`);
  return respuesta.json();
}

/**
 * Tapa todo lo que queda fuera del municipio con el color de fondo del estilo y dibuja su borde.
 * Va encima del mapa base (también de los rótulos y edificios) y debajo de las capas propias.
 */
export async function agregarMascara(mapa: MapaML, colorBorde: string): Promise<void> {
  const municipio = await cargar<FeatureCollection>("territorio/municipio.geojson");
  if (mapa.getSource("municipio")) return;
  const fondo = mapa.getStyle().layers.find((capa) => capa.type === "background");
  const colorFondo = fondo?.paint?.["background-color"] ?? "#f2f3f0";

  mapa.addSource("municipio", { type: "geojson", data: municipio });
  mapa.addLayer({
    id: "fuera-del-municipio",
    type: "fill",
    source: "municipio",
    filter: ["==", ["get", "parte"], "fuera"],
    paint: { "fill-color": colorFondo },
  });
  mapa.addLayer({
    id: "borde-municipio",
    type: "line",
    source: "municipio",
    filter: ["==", ["get", "parte"], "municipio"],
    paint: { "line-color": colorBorde, "line-width": 1.5 },
  });
}
