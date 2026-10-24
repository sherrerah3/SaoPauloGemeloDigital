import type { FeatureCollection } from "geojson";
import { useEffect, useRef, useState } from "react";
import { agregarMascara, estiloSaoPaulo, LIMITES_NAVEGACION } from "../componentes/mapaBase";
import {
  type CameraOptions,
  type ExpressionSpecification,
  type LayerSpecification,
  Map as MapaML,
  type MapLayerMouseEvent,
  NavigationControl,
  Popup,
} from "../componentes/maplibre";
import { cargar } from "../datos";
import { useTema } from "../tema";

// Colores oficiales de Metrô y CPTM: el nombre de cada línea es su color, así que se respetan.
const LINEAS: Record<number, { nombre: string; color: string }> = {
  1: { nombre: "1 Azul", color: "#0455a1" },
  2: { nombre: "2 Verde", color: "#007e5e" },
  3: { nombre: "3 Vermelha", color: "#ee372f" },
  4: { nombre: "4 Amarela", color: "#fed304" },
  5: { nombre: "5 Lilás", color: "#9b3894" },
  15: { nombre: "15 Prata", color: "#9e9e9e" },
  7: { nombre: "7 Rubi", color: "#ca016b" },
  8: { nombre: "8 Diamante", color: "#97a098" },
  9: { nombre: "9 Esmeralda", color: "#01a9a7" },
  10: { nombre: "10 Turquesa", color: "#049fc3" },
  11: { nombre: "11 Coral", color: "#f68368" },
  12: { nombre: "12 Safira", color: "#133c8d" },
  13: { nombre: "13 Jade", color: "#00b352" },
};
const COLOR_POR_LINEA: ExpressionSpecification = [
  "match",
  ["get", "codigo_linea"],
  ...Object.entries(LINEAS).flatMap(([codigo, l]) => [Number(codigo), l.color]),
  "#555555",
] as unknown as ExpressionSpecification;

interface Capa {
  id: string;
  titulo: string;
  archivo: string;
  fuente: string;
  muestra: string;
  capas: Omit<LayerSpecification, "source">[];
  popup?: (p: Record<string, unknown>) => string;
}

// Capa B del plan. Se bajan solo cuando se encienden (las paradas pesan ~2 MB).
const CAPAS: Capa[] = [
  {
    id: "metro",
    titulo: "Metro",
    archivo: "transporte/metro.geojson",
    fuente: "F35",
    muestra: "#0455a1",
    capas: [{ id: "metro", type: "line", paint: { "line-color": COLOR_POR_LINEA, "line-width": 4 } }],
    popup: (p) => `Metrô, línea ${p.codigo_linea} ${p.nombre_linea}<br><span class="popup-unidad">${p.operador}</span>`,
  },
  {
    id: "tren",
    titulo: "Tren CPTM",
    archivo: "transporte/tren.geojson",
    fuente: "F31",
    muestra: "#ca016b",
    capas: [
      { id: "tren", type: "line", paint: { "line-color": COLOR_POR_LINEA, "line-width": 3, "line-dasharray": [2, 1] } },
    ],
    popup: (p) => `Tren, línea ${p.codigo_linea} ${p.nombre_linea}<br><span class="popup-unidad">${p.operador}</span>`,
  },
  {
    id: "estaciones",
    titulo: "Estaciones de metro",
    archivo: "transporte/estaciones.geojson",
    fuente: "F36",
    muestra: "#ffffff",
    capas: [
      {
        id: "estaciones",
        type: "circle",
        paint: {
          "circle-radius": 5,
          "circle-color": "#ffffff",
          "circle-stroke-color": COLOR_POR_LINEA,
          "circle-stroke-width": 3,
        },
      },
    ],
    popup: (p) =>
      `<strong>${p.nombre_estacion}</strong><br><span class="popup-unidad">Línea ${p.codigo_linea}, ${String(p.situacion).toLowerCase()}</span>`,
  },
  {
    id: "red_bus",
    titulo: "Red de bus",
    archivo: "transporte/red_bus.geojson",
    fuente: "F29",
    muestra: "#eb6834",
    capas: [
      {
        id: "red_bus",
        type: "line",
        paint: {
          "line-color": "#eb6834",
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.6, 15, 2],
          "line-opacity": 0.8,
        },
      },
    ],
  },
  {
    id: "paradas",
    titulo: "Paradas de bus",
    archivo: "transporte/paradas.geojson",
    fuente: "F30",
    muestra: "#eb6834",
    capas: [
      {
        id: "paradas",
        type: "circle",
        minzoom: 12.5,
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 13, 2, 17, 5],
          "circle-color": "#eb6834",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1,
        },
      },
    ],
    popup: (p) => `Parada ${p.codigo_parada}<br><span class="popup-unidad">${p.calle_numero ?? ""}</span>`,
  },
  {
    id: "distritos",
    titulo: "Distritos",
    archivo: "territorio/distritos.geojson",
    fuente: "GeoSampa",
    muestra: "#2a78d6",
    capas: [
      { id: "distritos", type: "line", paint: { "line-color": "#2a78d6", "line-width": 1.2, "line-opacity": 0.9 } },
    ],
  },
  {
    id: "subprefeituras",
    titulo: "Subprefeituras",
    archivo: "territorio/subprefeituras.geojson",
    fuente: "GeoSampa",
    muestra: "#6250d6",
    capas: [{ id: "subprefeituras", type: "line", paint: { "line-color": "#6250d6", "line-width": 2.2 } }],
  },
];
const CAPAS_PENDIENTES = [
  "Estaciones de tren (candidata F42)",
  "Favelas, sin campos sensibles (F32)",
  "Equipamientos deportivos (F33, F34)",
  "Escuelas (F39, F40)",
  "Densidad por sector censal (F41, requiere PMTiles)",
];
const INICIALES = {
  metro: true,
  tren: true,
  estaciones: true,
  red_bus: false,
  paradas: false,
  distritos: false,
  subprefeituras: false,
};

const COLOR_BORDE_MUNICIPIO = { claro: "#52514e", oscuro: "#c3c2b7" };

// Avenida Paulista; los edificios 3D aparecen desde zoom 14.
const CAMARA_INICIAL: CameraOptions = { center: [-46.6555, -23.5613], zoom: 14.2, pitch: 60, bearing: -20 };

type EstadoCapa = "cargando" | "error";
const ESTADO_VISIBLE: Record<string, string> = { cargando: "…", error: "sin datos" };

/** Un popup compartido: clic en cualquier capa que tenga `popup` muestra sus datos. */
function registrarPopups(m: MapaML) {
  const popup = new Popup({ closeButton: false, offset: 8 });
  for (const capa of CAPAS) {
    if (!capa.popup) continue;
    const contenido = capa.popup;
    for (const { id } of capa.capas) {
      m.on("click", id, (e: MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (f) popup.setLngLat(e.lngLat).setHTML(contenido(f.properties)).addTo(m);
      });
      m.on("mouseenter", id, () => {
        m.getCanvas().style.cursor = "pointer";
      });
      m.on("mouseleave", id, () => {
        m.getCanvas().style.cursor = "";
      });
    }
  }
}

export default function Mapa3D() {
  const tema = useTema();
  const contenedor = useRef<HTMLDivElement>(null);
  const camara = useRef<CameraOptions>(CAMARA_INICIAL);
  const [mapa, setMapa] = useState<MapaML | null>(null);
  const [visibles, setVisibles] = useState<Record<string, boolean>>(INICIALES);
  const [estados, setEstados] = useState<Record<string, EstadoCapa>>({});

  // Crea el mapa. Al cambiar de tema se vuelve a crear con el otro estilo, en la misma posición.
  useEffect(() => {
    let creado: MapaML | null = null;
    let cancelado = false;

    estiloSaoPaulo("3d", tema).then((estilo) => {
      if (cancelado) return;
      const m = new MapaML({
        container: contenedor.current!,
        style: estilo,
        ...camara.current,
        minZoom: 9,
        maxBounds: LIMITES_NAVEGACION,
        attributionControl: { compact: true },
      });
      creado = m;
      m.addControl(new NavigationControl({ visualizePitch: true }), "top-right");
      registrarPopups(m);
      m.on("moveend", () => {
        camara.current = { center: m.getCenter(), zoom: m.getZoom(), pitch: m.getPitch(), bearing: m.getBearing() };
      });
      m.on("load", async () => {
        await agregarMascara(m, COLOR_BORDE_MUNICIPIO[tema]);
        setMapa(m);
      });
    });

    return () => {
      cancelado = true;
      setMapa(null);
      creado?.remove();
    };
  }, [tema]);

  // Enciende o apaga capas; la primera vez que se enciende una, baja su archivo.
  useEffect(() => {
    if (!mapa) return;
    let vigente = true;

    const marcar = (id: string, estado: EstadoCapa | null) =>
      setEstados(({ [id]: _anterior, ...resto }) => (estado ? { ...resto, [id]: estado } : resto));

    const agregarCapa = (capa: Capa) => {
      marcar(capa.id, "cargando");
      cargar<FeatureCollection>(capa.archivo)
        .then((datos) => {
          marcar(capa.id, null);
          // Si el mapa se recreó o la capa ya está, la siguiente pasada del efecto se encarga.
          if (!vigente || mapa.getSource(capa.id)) return;
          mapa.addSource(capa.id, { type: "geojson", data: datos });
          for (const sub of capa.capas) mapa.addLayer({ ...sub, source: capa.id } as LayerSpecification);
        })
        .catch(() => marcar(capa.id, "error"));
    };

    for (const capa of CAPAS) {
      const visible = visibles[capa.id] ?? false;
      if (mapa.getSource(capa.id)) {
        for (const sub of capa.capas) mapa.setLayoutProperty(sub.id, "visibility", visible ? "visible" : "none");
      } else if (visible) {
        agregarCapa(capa);
      }
    }
    return () => {
      vigente = false;
    };
  }, [mapa, visibles]);

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <h1>La ciudad en tres dimensiones</h1>
        <p className="entrada">
          Edificios de OpenStreetMap extruidos sobre el mapa base de OpenFreeMap, con las capas oficiales de GeoSampa
          encima. Arrastra con clic derecho (o dos dedos) para inclinar y girar; haz clic en una línea, estación o
          parada.
        </p>
      </header>

      <div className="mapa-3d-contenedor">
        <div
          ref={contenedor}
          className="mapa mapa-3d"
          role="img"
          aria-label="Mapa 3D de São Paulo con capas de transporte"
        />
        {!mapa && <p className="mapa-cargando">Cargando São Paulo…</p>}
        <div className="panel-capas">
          <h2>Capas</h2>
          {CAPAS.map((c) => (
            <label key={c.id} className="capa">
              <input
                type="checkbox"
                checked={visibles[c.id] ?? false}
                onChange={(e) => setVisibles((v) => ({ ...v, [c.id]: e.target.checked }))}
              />
              <span className="muestra-linea" style={{ background: c.muestra }} />
              {c.titulo}
              <span className="capa-fuente">{ESTADO_VISIBLE[estados[c.id]] ?? c.fuente}</span>
            </label>
          ))}
          {visibles.paradas && <p className="capas-nota">Las paradas aparecen al acercarse.</p>}
          {(visibles.metro || visibles.tren) && (
            <ul className="leyenda-lineas" aria-label="Líneas de metro y tren">
              {Object.entries(LINEAS).map(([codigo, l]) => (
                <li key={codigo}>
                  <span className="muestra-linea" style={{ background: l.color }} />
                  {l.nombre}
                </li>
              ))}
            </ul>
          )}
          <p className="capas-pendientes-titulo">Próximas capas</p>
          <ul className="capas-pendientes">
            {CAPAS_PENDIENTES.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      </div>
      <p className="nota">
        La altura de los edificios es la de OpenStreetMap, no la del LiDAR de la Prefeitura (fuera del lago en v1).
        Muchos edificios no tienen altura registrada y aparecen con una altura por defecto. La red de bus es la unión de
        los 2.326 recorridos (F29): cada calle se dibuja una vez aunque pasen varias líneas. GeoSampa publica sus capas
        bajo CC BY-SA en el portal; se atribuyen aquí aunque algunas fichas digan «no declara».
      </p>
    </section>
  );
}
