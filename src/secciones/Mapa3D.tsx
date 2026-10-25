import type { Feature, FeatureCollection } from "geojson";
import { useEffect, useRef, useState } from "react";
import { agregarMascara, estiloSaoPaulo, LIMITES_NAVEGACION } from "../componentes/mapaBase";
import {
  type CameraOptions,
  type ExpressionSpecification,
  type GeoJSONSource,
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
  fuente: string;
  muestra: string;
  capas: Omit<LayerSpecification, "source">[];
  popup?: (p: Record<string, unknown>) => string;
  /** Un solo archivo, que se baja la primera vez que se enciende la capa. */
  archivo?: string;
  /** O una carpeta partida en celdas (build_web.py): se bajan solo las cercanas, desde este zoom. */
  celdas?: { carpeta: string; desdeZoom: number };
}

interface IndiceCeldas {
  tamano_celda: number;
  celdas: string[];
}

// Capa B del plan. Se bajan solo cuando se encienden; la red de bus y las paradas, además,
// solo al acercarse y por zonas (pesan unos 3 y 4 MB en total).
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
    celdas: { carpeta: "transporte/red_bus", desdeZoom: 12 },
    fuente: "F29",
    muestra: "#eb6834",
    capas: [
      {
        id: "red_bus",
        type: "line",
        minzoom: 12,
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
    celdas: { carpeta: "transporte/paradas", desdeZoom: 13.5 },
    fuente: "F30",
    muestra: "#eb6834",
    capas: [
      {
        id: "paradas",
        type: "circle",
        minzoom: 13.5,
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
    id: "escuelas_infantil",
    titulo: "Escuelas infantiles",
    archivo: "equipamientos/escuelas_infantil.geojson",
    fuente: "F39",
    muestra: "#f2b134",
    capas: [{ id: "escuelas_infantil", type: "circle", paint: circulo("#f2b134") }],
    popup: (p) =>
      `<strong>${p.nombre}</strong><br><span class="popup-unidad">Educación infantil, ${p.direccion}</span>`,
  },
  {
    id: "escuelas_basica",
    titulo: "Escuelas fundamental y media",
    archivo: "equipamientos/escuelas_basica.geojson",
    fuente: "F40",
    muestra: "#c8702a",
    capas: [{ id: "escuelas_basica", type: "circle", paint: circulo("#c8702a") }],
    popup: (p) => `<strong>${p.nombre}</strong><br><span class="popup-unidad">Escuela pública, ${p.direccion}</span>`,
  },
  {
    id: "deporte",
    titulo: "Centros deportivos",
    archivo: "equipamientos/centros_deportivos.geojson",
    fuente: "F33",
    muestra: "#2e9e5b",
    capas: [{ id: "deporte", type: "circle", paint: circulo("#2e9e5b", 6) }],
    popup: (p) => `<strong>${p.nombre}</strong><br><span class="popup-unidad">${p.tipo}</span>`,
  },
  {
    id: "estadios",
    titulo: "Estadios",
    archivo: "equipamientos/estadios.geojson",
    fuente: "F34",
    muestra: "#1b6e3c",
    capas: [{ id: "estadios", type: "circle", paint: circulo("#1b6e3c", 7) }],
    popup: (p) => `<strong>${p.nombre}</strong><br><span class="popup-unidad">${p.tipo}</span>`,
  },
  {
    id: "favelas",
    titulo: "Favelas",
    archivo: "gente/favelas.geojson",
    fuente: "F32",
    muestra: "#c0504d",
    capas: [
      { id: "favelas", type: "fill", paint: { "fill-color": "#c0504d", "fill-opacity": 0.35 } },
      { id: "favelas-borde", type: "line", paint: { "line-color": "#c0504d", "line-width": 1 } },
    ],
    // Sin la calle ni la propiedad del terreno: son campos Sensibles del Diccionario.
    popup: (p) =>
      `<strong>${p.nombre}</strong><br><span class="popup-unidad">Favela, ${p.domicilios ?? "s. d."} domicilios${p.anio_implantacion ? `, desde ${p.anio_implantacion}` : ""}</span>`,
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
const CAPAS_PENDIENTES = ["Estaciones de tren CPTM (no están en el catálogo)", "Densidad por sector censal (F41)"];
const INICIALES: Record<string, boolean> = { metro: true, tren: true, estaciones: true };

function circulo(color: string, radio = 4) {
  return {
    "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, radio * 0.6, 16, radio * 1.5],
    "circle-color": color,
    "circle-stroke-color": "#ffffff",
    "circle-stroke-width": 1,
  } as LayerSpecification["paint"];
}

// Las celdas a más de este número de celdas del centro no se bajan: con el mapa inclinado,
// el horizonte llega lejos y casi no se ve lo que hay allí.
const RADIO_CELDAS = 2;

/** Celdas que tocan la vista, sin pasar de RADIO_CELDAS alrededor del centro. */
function celdasVisibles(m: MapaML, tamano: number): string[] {
  const b = m.getBounds();
  const c = m.getCenter();
  const [cx, cy] = [Math.floor(c.lng / tamano), Math.floor(c.lat / tamano)];
  const rango = (desde: number, hasta: number, centro: number) => {
    const valores: number[] = [];
    for (let v = Math.max(desde, centro - RADIO_CELDAS); v <= Math.min(hasta, centro + RADIO_CELDAS); v++) {
      valores.push(v);
    }
    return valores;
  };
  const xs = rango(Math.floor(b.getWest() / tamano), Math.floor(b.getEast() / tamano), cx);
  const ys = rango(Math.floor(b.getSouth() / tamano), Math.floor(b.getNorth() / tamano), cy);
  return xs.flatMap((x) => ys.map((y) => `${x}_${y}`));
}

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
  // Celdas ya bajadas por capa. Se vacía al recrear el mapa, porque las fuentes se pierden.
  const celdas = useRef(new Map<string, { cargadas: Set<string>; features: Feature[] }>());

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
      celdas.current = new Map();
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

  // Enciende o apaga capas; la primera vez que se enciende una, baja su archivo (o sus celdas).
  useEffect(() => {
    if (!mapa) return;
    let vigente = true;

    const marcar = (id: string, estado: EstadoCapa | null) =>
      setEstados(({ [id]: _anterior, ...resto }) => (estado ? { ...resto, [id]: estado } : resto));

    const agregarFuente = (capa: Capa, datos: FeatureCollection) => {
      mapa.addSource(capa.id, { type: "geojson", data: datos });
      for (const sub of capa.capas) mapa.addLayer({ ...sub, source: capa.id } as LayerSpecification);
    };

    const agregarCapa = (capa: Capa) => {
      if (!capa.archivo) return;
      marcar(capa.id, "cargando");
      cargar<FeatureCollection>(capa.archivo)
        .then((datos) => {
          marcar(capa.id, null);
          // Si el mapa se recreó o la capa ya está, la siguiente pasada del efecto se encarga.
          if (!vigente || mapa.getSource(capa.id)) return;
          agregarFuente(capa, datos);
        })
        .catch(() => marcar(capa.id, "error"));
    };

    // Baja las celdas cercanas que falten y las suma a lo que ya tiene la fuente.
    const actualizarCeldas = () => {
      for (const capa of CAPAS) {
        if (!capa.celdas || !visibles[capa.id] || mapa.getZoom() < capa.celdas.desdeZoom) continue;
        const { carpeta } = capa.celdas;
        const estado = celdas.current.get(capa.id) ?? { cargadas: new Set<string>(), features: [] };
        celdas.current.set(capa.id, estado);
        cargar<IndiceCeldas>(`${carpeta}/indice.json`)
          .then((indice) => {
            const existentes = new Set(indice.celdas);
            const nuevas = celdasVisibles(mapa, indice.tamano_celda).filter(
              (c) => existentes.has(c) && !estado.cargadas.has(c),
            );
            if (!nuevas.length) return;
            for (const c of nuevas) estado.cargadas.add(c);
            marcar(capa.id, "cargando");
            return Promise.all(nuevas.map((c) => cargar<FeatureCollection>(`${carpeta}/${c}.geojson`))).then(
              (partes) => {
                marcar(capa.id, null);
                // Si el mapa se recreó (cambio de tema), este estado ya no es el suyo.
                if (celdas.current.get(capa.id) !== estado) return;
                for (const parte of partes) estado.features.push(...parte.features);
                (mapa.getSource(capa.id) as GeoJSONSource | undefined)?.setData({
                  type: "FeatureCollection",
                  features: estado.features,
                });
              },
            );
          })
          .catch(() => marcar(capa.id, "error"));
      }
    };

    for (const capa of CAPAS) {
      const visible = visibles[capa.id] ?? false;
      if (mapa.getSource(capa.id)) {
        for (const sub of capa.capas) mapa.setLayoutProperty(sub.id, "visibility", visible ? "visible" : "none");
      } else if (visible && capa.celdas) {
        agregarFuente(capa, { type: "FeatureCollection", features: [] });
      } else if (visible) {
        agregarCapa(capa);
      }
    }
    actualizarCeldas();
    mapa.on("moveend", actualizarCeldas);
    return () => {
      vigente = false;
      mapa.off("moveend", actualizarCeldas);
    };
  }, [mapa, visibles]);

  const conCeldas = CAPAS.filter((c) => c.celdas && visibles[c.id]);

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
          {conCeldas.length > 0 && (
            <p className="capas-nota">
              {conCeldas.map((c) => c.titulo).join(" y ")}: aparecen al acercarse y se cargan solo por la zona que ves.
            </p>
          )}
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
        La altura de los edificios es la de OpenStreetMap (etiqueta de altura o número de pisos × 3,66 m), no la del
        LiDAR de la Prefeitura, que está fuera del lago. Los que no tienen ninguno de los dos datos aparecen con 5 m: en
        una muestra de octubre de 2026 eran cerca del 10 % de los edificios alrededor de la Paulista y el 20 % en Capão
        Redondo. La red de bus es la unión de los 2.326 recorridos (F29): cada calle se dibuja una vez aunque pasen
        varias líneas. GeoSampa publica sus capas bajo CC BY-SA en el portal; se atribuyen aquí aunque algunas fichas
        digan «no declara».
      </p>
    </section>
  );
}
