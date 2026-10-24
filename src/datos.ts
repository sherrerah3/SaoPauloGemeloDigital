// Tipos del contrato de datos (sección 6 del plan) y carga de public/data/.

export type Tipo = "observado" | "estimado" | "proxy" | "declarado";
// «linea» se usa en F05 (pasajeros por línea de bus), que no tiene geografía.
export type Nivel = "municipio" | "subprefeitura" | "distrito" | "linea";

export interface Indicador {
  id: string;
  campo_lago: string;
  valor: number | null;
  unidad: string;
  nivel: Nivel;
  codigo_territorio: string;
  nombre_territorio: string;
  fuente_id: string;
  vigencia: string;
  tipo: Tipo;
  advertencia?: string | null;
  calculo?: string;
  fuentes_adicionales?: string[];
}

export interface ArchivoIndicadores {
  seccion: string;
  pregunta: string;
  generado: string;
  indicadores: Indicador[];
}

export interface IndiceSeccion {
  seccion: string;
  anios: string[];
  territorios: { nivel: Nivel; codigo_territorio: string; nombre_territorio: string }[];
}

export interface Fuente {
  fuente_id: string;
  nombre: string;
  entidad: string;
  tipo_publicador: string;
  url: string;
  formato: string;
  licencia: string;
  cobertura: string;
  periodo: string;
  frecuencia: string;
  fecha_prueba: string;
  estado: string;
  observaciones: string;
}

export interface CampoDiccionario {
  fuente_id: string;
  campo: string;
  nombre_original: string;
  significado: string;
  tipo_dato: string;
  unidad: string;
  clasificacion: string;
  transformacion: string;
  pregunta: string;
}

const cache = new Map<string, Promise<unknown>>();

export function cargar<T>(ruta: string): Promise<T> {
  if (!cache.has(ruta)) {
    cache.set(
      ruta,
      fetch(`${import.meta.env.BASE_URL}data/${ruta}`).then((r) => {
        if (!r.ok) throw new Error(`No se pudo leer ${ruta} (${r.status})`);
        return r.json();
      }),
    );
  }
  return cache.get(ruta) as Promise<T>;
}

/** Para filtrar indicadores con cifra: después del filtro, `valor` ya no es null. */
export function tieneValor(i: Indicador): i is Indicador & { valor: number } {
  return i.valor !== null;
}

/** El id de un indicador sin la parte de territorio y año: «empleos_formales_participacion». */
export function claveIndicador(i: Indicador): string {
  return i.id.slice(0, i.id.indexOf(`_${i.nivel}_`));
}

const formatoEntero = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const formatoDecimal = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

export function formatear(valor: number | null, unidad = ""): string {
  if (valor === null || Number.isNaN(valor)) return "Sin dato";
  if (unidad.startsWith("%")) return `${formatoDecimal.format(valor)} %`;
  return Math.abs(valor) >= 100 ? formatoEntero.format(valor) : formatoDecimal.format(valor);
}

export function formatearCorto(valor: number): string {
  if (Math.abs(valor) >= 1_000_000) return `${formatoDecimal.format(valor / 1_000_000)} M`;
  if (Math.abs(valor) >= 1_000) return `${formatoEntero.format(valor / 1_000)} mil`;
  return formatoDecimal.format(valor);
}
