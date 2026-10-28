import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import CodigoPregunta from "../componentes/CodigoPregunta";
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
  formatearCorto,
  type Indicador,
  type IndiceSeccion,
  metricaPorTerritorio,
  tieneValor,
} from "../datos";
import { useParametro } from "../rutas";

// «anios» limita los años: el empleo por sexo existe desde 2022 y por raza o color desde 2023.
// «municipal» indica si el municipio tiene la cifra (la participación y la densidad no).
const METRICAS: { clave: string; etiqueta: string; anios?: string[]; municipal: boolean }[] = [
  { clave: "empleos_formales", etiqueta: "Empleos formales", municipal: true },
  { clave: "empleos_formales_participacion", etiqueta: "Participación en el municipio", municipal: false },
  { clave: "empleos_formales_por_km2", etiqueta: "Empleos por km²", municipal: false },
  { clave: "establecimientos_formales", etiqueta: "Establecimientos formales", municipal: true },
  {
    clave: "empleos_femenino_pct",
    etiqueta: "Empleos ocupados por mujeres",
    anios: ["2022", "2023", "2024"],
    municipal: true,
  },
  {
    clave: "empleos_raza_preta_parda_pct",
    etiqueta: "Empleos de personas pretas o pardas",
    anios: ["2023", "2024"],
    municipal: true,
  },
];

const RAZAS = [
  { clave: "branca", etiqueta: "Blanca" },
  { clave: "parda", etiqueta: "Parda" },
  { clave: "preta", etiqueta: "Preta" },
  { clave: "amarela", etiqueta: "Amarilla" },
  { clave: "indigena", etiqueta: "Indígena" },
  { clave: "nao_identificada", etiqueta: "No identificada" },
];

export default function Empleo() {
  const [indice, setIndice] = useState<IndiceSeccion>();
  const [anioUrl, setAnio] = useParametro("anio");
  const [datosAnio, setDatosAnio] = useState<Indicador[]>([]);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [distrito, setDistrito] = useParametro("distrito");
  const [serie, setSerie] = useState<Indicador[]>([]);

  useEffect(() => {
    cargar<IndiceSeccion>("indicadores/empleo/indice.json").then(setIndice);
  }, []);

  // Lo que viene en la URL se valida; si no sirve, se usa el valor por defecto.
  const def = METRICAS.find((m) => m.clave === metricaUrl) ?? METRICAS[0];
  const metrica = def.clave;
  const anios = def.anios ?? indice?.anios ?? [];
  const anio = anioUrl && anios.includes(anioUrl) ? anioUrl : anios.at(-1);

  useEffect(() => {
    if (!anio) return;
    cargar<ArchivoIndicadores>(`indicadores/empleo/anio_${anio}.json`).then((a) => setDatosAnio(a.indicadores));
  }, [anio]);

  useEffect(() => {
    const ruta = distrito ? `serie_distrito_${distrito}` : "serie_municipio_MSP";
    cargar<ArchivoIndicadores>(`indicadores/empleo/${ruta}.json`).then((a) => setSerie(a.indicadores));
  }, [distrito]);

  const { valores, ranking, unidad } = useMemo(() => metricaPorTerritorio(datosAnio, metrica), [datosAnio, metrica]);

  const territorio = distrito ?? "MSP";
  const busca = (clave: string) =>
    datosAnio.find((i) => i.codigo_territorio === territorio && claveIndicador(i) === clave);
  const nombreTerritorio = busca("empleos_formales")?.nombre_territorio ?? "Município de São Paulo";

  const defSerie = distrito || def.municipal ? def : METRICAS[0];
  const serieMetrica = serie
    .filter((i) => claveIndicador(i) === defSerie.clave)
    .map((i) => ({ anio: i.vigencia, valor: i.valor }));
  const unidadSerie = serie.find((i) => claveIndicador(i) === defSerie.clave)?.unidad;
  const periodoSerie = serieMetrica.length ? `${serieMetrica[0].anio}-${serieMetrica.at(-1)?.anio}` : "";

  const razas = RAZAS.map((r) => ({ ...r, indicador: busca(`empleos_raza_${r.clave}_pct`) }));
  const hayRaza = razas.some((r) => r.indicador);

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <p className="rotulo-pregunta">
          <CodigoPregunta codigo="P2" /> Pregunta 2
        </p>
        <h1>¿Cómo se distribuye el empleo formal entre los distritos?</h1>
        <p className="entrada">
          Empleos y establecimientos con registro formal (RAIS) en los 96 distritos, 2011 a 2024. Muestra dónde trabaja
          la gente, no dónde vive. Haz clic en un distrito para ver su serie.
        </p>
      </header>

      {/* Los años cambian con el indicador: por sexo desde 2022, por raza o color desde 2023. */}
      <SelectorAnio etiqueta="Año" anios={anios} valor={anio} onCambiar={setAnio} />

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
        {distrito && (
          <button type="button" className="boton-secundario" onClick={() => setDistrito(null)}>
            Volver al municipio
          </button>
        )}
      </div>

      <div className="rejilla-tarjetas">
        <TarjetaIndicador
          titulo={`Empleos formales en ${nombreTerritorio}`}
          indicador={busca("empleos_formales")}
          destacado
        />
        <TarjetaIndicador
          titulo={`Establecimientos en ${nombreTerritorio}`}
          indicador={busca("establecimientos_formales")}
        />
        {distrito && (
          <TarjetaIndicador
            titulo="Participación en el municipio"
            indicador={busca("empleos_formales_participacion")}
          />
        )}
        {busca("empleos_femenino_pct") && (
          <TarjetaIndicador titulo="Empleos ocupados por mujeres" indicador={busca("empleos_femenino_pct")} />
        )}
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>
            {def.etiqueta} por distrito, {anio}
          </h2>
          <MapaDistritos valores={valores} unidad={unidad} seleccionado={distrito} onSeleccionar={setDistrito} />
        </div>

        <RankingDistritos
          titulo={`Los 10 distritos con más ${def.etiqueta.toLowerCase()}`}
          ranking={ranking}
          unidad={unidad}
          seleccionado={distrito}
          onSeleccionar={setDistrito}
        >
          <p className="nota">Excluye las filas «inválidos» y «no localizados», que se conservan en el lago.</p>
        </RankingDistritos>
      </div>

      {hayRaza && (
        <div className="panel">
          <h2>
            Empleos por raza o color en {nombreTerritorio}, {anio}
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={razas
                .filter((r) => r.indicador && tieneValor(r.indicador))
                .map((r) => ({
                  nombre: r.etiqueta,
                  valor: r.indicador?.valor,
                }))}
              layout="vertical"
              margin={{ left: 8, right: 48 }}
              barCategoryGap={4}
            >
              <CartesianGrid horizontal={false} stroke="var(--grilla)" />
              <XAxis type="number" unit=" %" {...EJE} />
              <YAxis type="category" dataKey="nombre" width={110} {...EJE} />
              <Tooltip
                cursor={{ fill: "var(--superficie-2)" }}
                formatter={(v) => [formatear(Number(v), "%"), "De los empleos"]}
                {...ESTILO_TOOLTIP}
              />
              <Bar dataKey="valor" fill={SERIE_1} radius={[0, 4, 4, 0]}>
                <LabelList
                  dataKey="valor"
                  position="right"
                  formatter={(v: unknown) => formatear(Number(v), "%")}
                  style={{ fill: "var(--texto-2)", fontSize: 12 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="nota">
            Fuente {razas.find((r) => r.indicador)?.indicador?.fuente_id} (RAIS vía Infocidade). Raza o color es un dato
            sensible: solo se publica como porcentaje, y una categoría con menos de 10 empleos no se muestra. En 2023,
            el 10,8 % de los empleos del municipio no tenía raza o color registrada; en 2024, el 2,4 %.
          </p>
        </div>
      )}

      <div className="panel">
        <h2>
          {defSerie.etiqueta} en {nombreTerritorio}, {periodoSerie}
        </h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={serieMetrica} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid vertical={false} stroke="var(--grilla)" />
            <XAxis dataKey="anio" {...EJE} />
            <YAxis tickFormatter={formatearCorto} width={60} {...EJE} />
            {/* El quiebre solo se marca si la serie empieza antes: en sexo y raza es su primer año. */}
            {serieMetrica[0]?.anio < "2022" && (
              <ReferenceLine
                x="2022"
                stroke="var(--texto-tenue)"
                strokeDasharray="4 4"
                label={{ value: "Quiebre RAIS", fontSize: 11, fill: "var(--texto-tenue)", position: "insideTopLeft" }}
              />
            )}
            <Tooltip formatter={(v) => [formatear(Number(v), unidadSerie), defSerie.etiqueta]} {...ESTILO_TOOLTIP} />
            <Line
              dataKey="valor"
              stroke={SERIE_1}
              strokeWidth={2}
              dot={{ r: 4, fill: SERIE_1, strokeWidth: 2, stroke: "var(--superficie)" }}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="nota">
          Desde 2022 la RAIS cambió la forma de captar los datos (nota técnica del MTE): los saltos alrededor de ese
          año, como el de Brás en 2022, pueden ser del registro y no de la economía.
        </p>
      </div>

      <aside className="limitacion">
        <strong>Lo que esta sección no muestra todavía:</strong> empleo por sector económico (no está en el lago). El
        empleo por sexo cubre 2022-2024 (F13-F15) y por raza o color 2023-2024 (F16-F17).
      </aside>
    </section>
  );
}
