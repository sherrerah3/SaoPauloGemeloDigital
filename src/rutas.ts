import { useCallback, useEffect, useState } from "react";

export interface Seccion {
  id: string;
  titulo: string;
  resumen: string;
  fuentes: string[];
  lista: boolean;
}

// Secciones de la v1 (sección 8 del plan). «lista» indica si ya tiene datos en public/data/.
export const SECCIONES: Seccion[] = [
  {
    id: "panorama",
    titulo: "Panorama",
    resumen: "Cifras clave de la ciudad y acceso a las dos preguntas.",
    fuentes: ["F01", "F08", "F04", "F05", "F11", "F12"],
    lista: true,
  },
  {
    id: "mapa",
    titulo: "Mapa 3D",
    resumen: "Edificios 3D y capas oficiales de GeoSampa.",
    fuentes: ["F29", "F30", "F31", "F32", "F33", "F34", "F35", "F36", "F39", "F40", "F41"],
    lista: true,
  },
  {
    id: "empleo",
    titulo: "Empleo",
    resumen: "P2 · Establecimientos y empleos formales por distrito.",
    fuentes: ["F11", "F12", "F13", "F14", "F15", "F16", "F17", "F22", "F23", "F24", "F28"],
    lista: true,
  },
  {
    id: "transporte",
    titulo: "Transporte y equipamientos",
    resumen: "P1 · Cobertura de transporte por distrito, pasajeros por línea, mercados, deporte y escuelas.",
    fuentes: ["F29", "F30", "F31", "F35", "F36", "F41", "F05", "F21", "F33", "F34", "F39", "F40"],
    lista: true,
  },
  {
    id: "gente",
    titulo: "Gente",
    resumen: "Población histórica, densidad por distrito, IDHM, nacimientos y favelas.",
    fuentes: ["F01", "F41", "F07", "F18", "F19", "F20", "F32"],
    lista: false,
  },
  {
    id: "municipio",
    titulo: "Municipio",
    resumen: "Ingresos y gastos por categoría 2016-2025 y establecimientos de salud.",
    fuentes: ["F04", "F03"],
    lista: false,
  },
  {
    id: "ambiente",
    titulo: "Ambiente",
    resumen: "Cobertura vegetal por subprefeitura y temperatura mínima.",
    fuentes: ["F25", "F26", "F27", "F06"],
    lista: false,
  },
  {
    id: "atlas",
    titulo: "Atlas y correlaciones",
    resumen: "Índice por distrito con pesos ajustables y correlaciones en dos escalas.",
    fuentes: [],
    lista: false,
  },
  {
    id: "fuentes",
    titulo: "Fuentes y método",
    resumen: "Catálogo y diccionario generados desde el Excel.",
    fuentes: [],
    lista: true,
  },
  {
    id: "no-cubrimos",
    titulo: "Lo que no cubrimos",
    resumen: "Lo que el lago no permite responder todavía.",
    fuentes: [],
    lista: true,
  },
];

// El hash lleva la sección y, después de «?», el estado de sus filtros:
// #transporte?metrica=paradas_por_km2&distrito=96. Así cada vista se puede compartir con un enlace.
const EVENTO_PARAMETROS = "parametros-url";

function partesHash(): [string, URLSearchParams] {
  const [ruta, consulta = ""] = window.location.hash.replace(/^#\/?/, "").split("?");
  return [ruta || "panorama", new URLSearchParams(consulta)];
}

export function useRuta(): string {
  const [ruta, setRuta] = useState(() => partesHash()[0]);
  useEffect(() => {
    const alCambiar = () => {
      const nueva = partesHash()[0];
      setRuta((actual) => {
        if (actual !== nueva) window.scrollTo({ top: 0 });
        return nueva;
      });
    };
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  return ruta;
}

/** Un filtro guardado en la URL. Cambiarlo reemplaza la entrada del historial (no agrega una). */
export function useParametro(clave: string): [string | null, (valor: string | null) => void] {
  const [valor, setValor] = useState(() => partesHash()[1].get(clave));

  useEffect(() => {
    const alCambiar = () => setValor(partesHash()[1].get(clave));
    window.addEventListener("hashchange", alCambiar);
    window.addEventListener(EVENTO_PARAMETROS, alCambiar);
    return () => {
      window.removeEventListener("hashchange", alCambiar);
      window.removeEventListener(EVENTO_PARAMETROS, alCambiar);
    };
  }, [clave]);

  const cambiar = useCallback(
    (nuevo: string | null) => {
      const [ruta, parametros] = partesHash();
      if (nuevo === null) parametros.delete(clave);
      else parametros.set(clave, nuevo);
      const consulta = parametros.toString();
      window.history.replaceState(null, "", `#${ruta}${consulta ? `?${consulta}` : ""}`);
      window.dispatchEvent(new Event(EVENTO_PARAMETROS));
    },
    [clave],
  );

  return [valor, cambiar];
}
