import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EJE, ESTILO_TOOLTIP, SERIE_1 } from "../componentes/graficos";
import MapaDistritos from "../componentes/MapaDistritos";
import RankingDistritos from "../componentes/RankingDistritos";
import SelectorAnio from "../componentes/SelectorAnio";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import {
  type ArchivoIndicadores,
  cargar,
  claveIndicador,
  formatear,
  type Indicador,
  metricaPorTerritorio,
} from "../datos";
import { useParametro } from "../rutas";

const METRICAS = [
  { clave: "cobertura_vegetal_por_hab", etiqueta: "Vegetación por habitante" },
  { clave: "cobertura_vegetal_km2", etiqueta: "Superficie con vegetación" },
] as const;
type Clave = (typeof METRICAS)[number]["clave"];

// Cada año se midió distinto (satélite SPOT, RapidEye, fotos aéreas con LiDAR): no se comparan.
const ANIOS = ["2020", "2015", "2010"];

// Temperatura mínima (F06): una sola estación. La normal es el promedio de 30 años de la OMM.
const NORMAL = "1991-2020";
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** Eje Y ajustado a los datos, en grados enteros: con el 0 por defecto, la línea quedaría aplastada arriba. */
const dominioEnteros = ([min, max]: readonly [number, number]): [number, number] => [Math.floor(min), Math.ceil(max)];

export default function Ambiente() {
  const [datos, setDatos] = useState<Indicador[]>([]);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [anioUrl, setAnio] = useParametro("anio");
  const [subprefeitura, setSubprefeitura] = useParametro("subprefeitura");
  const [temperatura, setTemperatura] = useState<Indicador[]>([]);
  const [anioTempUrl, setAnioTemp] = useParametro("anio_temp");
  const def = METRICAS.find((m) => m.clave === metricaUrl) ?? METRICAS[0];
  const metrica: Clave = def.clave;
  const anio = anioUrl && ANIOS.includes(anioUrl) ? anioUrl : ANIOS[0];

  useEffect(() => {
    cargar<ArchivoIndicadores>("indicadores/ambiente/subprefeituras.json").then((a) => setDatos(a.indicadores));
    cargar<ArchivoIndicadores>("indicadores/ambiente/temperatura.json").then((a) => setTemperatura(a.indicadores));
  }, []);

  // Temperatura: un índice por «clave|vigencia» y la serie anual, de la que salen los años disponibles.
  const indiceTemp = useMemo(
    () => new Map(temperatura.map((i) => [`${claveIndicador(i)}|${i.vigencia}`, i])),
    [temperatura],
  );
  const serieAnual = useMemo(
    () =>
      temperatura
        .filter((i) => claveIndicador(i) === "temp_min_anual")
        .map((i) => ({ anio: Number(i.vigencia), valor: i.valor }))
        .sort((a, b) => a.anio - b.anio),
    [temperatura],
  );
  const aniosTemp = useMemo(() => serieAnual.map((d) => String(d.anio)), [serieAnual]);
  // Por defecto el último año; un año de la URL que no está en la serie se ignora.
  const anioTemp = anioTempUrl && aniosTemp.includes(anioTempUrl) ? anioTempUrl : aniosTemp.at(-1);
  const normalAnual = indiceTemp.get(`temp_min_normal_anual|${NORMAL}`);
  const mensual = MESES.map((mes, k) => {
    const m = String(k + 1).padStart(2, "0");
    return {
      mes,
      anio: indiceTemp.get(`temp_min_mes|${anioTemp}-${m}`)?.valor ?? null,
      normal: indiceTemp.get(`temp_min_normal_m${m}|${NORMAL}`)?.valor ?? null,
    };
  });

  const delAnio = useMemo(() => datos.filter((i) => i.vigencia === anio), [datos, anio]);
  const { valores, ranking, unidad } = useMemo(
    () => metricaPorTerritorio(delAnio, metrica, "desc", "subprefeitura"),
    [delAnio, metrica],
  );

  const territorio = subprefeitura ?? "MSP";
  const busca = (clave: string) =>
    delAnio.find((i) => i.codigo_territorio === territorio && claveIndicador(i) === clave);
  const nombreTerritorio = busca(metrica)?.nombre_territorio ?? "Município de São Paulo";

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <h1>¿Cuánto verde tiene cada zona?</h1>
        <p className="entrada">
          Cobertura vegetal de la Secretaría del Verde y Medio Ambiente por subprefeitura, con la población de cada año.
          Haz clic en una subprefeitura para ver sus cifras.
        </p>
      </header>

      <SelectorAnio etiqueta="Año del mapeo" anios={ANIOS} valor={anio} onCambiar={setAnio} />

      <div className="filtros">
        <label>
          Indicador
          <select value={metrica} onChange={(e) => setMetrica(e.target.value)}>
            {METRICAS.map((m) => (
              <option key={m.clave} value={m.clave}>
                {m.etiqueta}
              </option>
            ))}
          </select>
        </label>
        {subprefeitura && (
          <button type="button" className="boton-secundario" onClick={() => setSubprefeitura(null)}>
            Volver al municipio
          </button>
        )}
      </div>

      <div className="rejilla-tarjetas">
        <TarjetaIndicador
          titulo={`Vegetación por habitante en ${nombreTerritorio}`}
          indicador={busca("cobertura_vegetal_por_hab")}
          destacado
        />
        <TarjetaIndicador titulo="Superficie con vegetación" indicador={busca("cobertura_vegetal_km2")} />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>
            {def.etiqueta} por subprefeitura, {anio}
          </h2>
          <MapaDistritos
            nivel="subprefeitura"
            valores={valores}
            unidad={unidad}
            seleccionado={subprefeitura}
            onSeleccionar={setSubprefeitura}
          />
        </div>
        <RankingDistritos
          titulo={`Las 10 subprefeituras con más ${def.etiqueta.toLowerCase()}`}
          ranking={ranking}
          unidad={unidad}
          seleccionado={subprefeitura}
          onSeleccionar={setSubprefeitura}
          columna="Subprefeitura"
        />
      </div>

      <aside className="limitacion">
        <strong>Antes de comparar años:</strong> 2010 se midió con imágenes del satélite SPOT, 2015 con RapidEye y 2020
        con fotos aéreas de 2017-2018 apoyadas en LiDAR. Las diferencias entre años son sobre todo de método, por eso la
        sección muestra un año a la vez.
      </aside>

      <header className="seccion-cabecera">
        <h2 className="subtitulo-seccion">¿Qué tan frías son las noches?</h2>
        <p className="entrada">
          Promedio mensual de las temperaturas mínimas del aire, de 1933 a 2025, que publica la Prefeitura con datos del
          Instituto Astronômico e Geofísico de la USP. Se compara cada año con la normal {NORMAL}.
        </p>
      </header>

      <SelectorAnio etiqueta="Año de la temperatura" anios={aniosTemp} valor={anioTemp} onCambiar={setAnioTemp} />

      <div className="rejilla-tarjetas">
        <TarjetaIndicador
          titulo={`Temperatura mínima media de ${anioTemp ?? "…"}`}
          indicador={anioTemp ? indiceTemp.get(`temp_min_anual|${anioTemp}`) : undefined}
          destacado
        />
        <TarjetaIndicador titulo={`Normal ${NORMAL}`} indicador={normalAnual} />
        <TarjetaIndicador
          titulo="Diferencia con la normal"
          indicador={anioTemp ? indiceTemp.get(`temp_min_anual_vs_normal|${anioTemp}`) : undefined}
        />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>
            Temperatura mínima media anual, {serieAnual[0]?.anio}-{serieAnual.at(-1)?.anio}
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={serieAnual} margin={{ left: 8, right: 16, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--grilla)" />
              <XAxis dataKey="anio" type="number" domain={["dataMin", "dataMax"]} {...EJE} />
              <YAxis domain={dominioEnteros} width={56} unit=" °C" {...EJE} />
              <Tooltip
                formatter={(v) => [`${formatear(Number(v))} °C`, "Mínima media anual"]}
                labelFormatter={(anio) => `Año ${anio}`}
                {...ESTILO_TOOLTIP}
              />
              {normalAnual?.valor != null && (
                <ReferenceLine
                  y={normalAnual.valor}
                  stroke="var(--texto-tenue)"
                  strokeDasharray="5 4"
                  label={{ value: `Normal ${NORMAL}`, position: "insideTopLeft", fill: "var(--texto-2)", fontSize: 12 }}
                />
              )}
              {anioTemp && <ReferenceLine x={Number(anioTemp)} stroke="var(--acento)" strokeOpacity={0.6} />}
              <Line dataKey="valor" stroke={SERIE_1} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h2>{anioTemp ?? "…"} mes a mes frente a la normal</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={mensual} margin={{ left: 8, right: 16, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--grilla)" />
              <XAxis dataKey="mes" {...EJE} />
              <YAxis domain={dominioEnteros} width={56} unit=" °C" {...EJE} />
              <Tooltip formatter={(v) => `${formatear(Number(v))} °C`} {...ESTILO_TOOLTIP} />
              <Legend />
              <Line name={`Año ${anioTemp ?? ""}`} dataKey="anio" stroke={SERIE_1} strokeWidth={2} dot={{ r: 3 }} />
              <Line
                name={`Normal ${NORMAL}`}
                dataKey="normal"
                stroke="var(--texto-tenue)"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <aside className="limitacion">
        <strong>Una cifra para toda la ciudad:</strong> la temperatura no se mide por lugar, barrio ni zona, así que no
        hay mapa de temperatura. Es una cifra general para São Paulo, medida en una estación meteorológica. Las normales
        y los promedios anuales se calculan de los doce meses de cada año. En 2025 los meses vienen redondeados a un
        decimal.
      </aside>
    </section>
  );
}
