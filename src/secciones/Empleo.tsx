import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import CodigoPregunta from "../componentes/CodigoPregunta";
import MapaDistritos from "../componentes/MapaDistritos";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import {
  type ArchivoIndicadores,
  cargar,
  claveIndicador,
  formatear,
  formatearCorto,
  type Indicador,
  type IndiceSeccion,
  tieneValor,
} from "../datos";
import { useParametro } from "../rutas";

const METRICAS = [
  { clave: "empleos_formales", etiqueta: "Empleos formales" },
  { clave: "empleos_formales_participacion", etiqueta: "Participación en el municipio" },
  { clave: "empleos_formales_por_km2", etiqueta: "Empleos por km²" },
  { clave: "establecimientos_formales", etiqueta: "Establecimientos formales" },
] as const;

const AZUL = "var(--serie-1)";

export default function Empleo() {
  const [indice, setIndice] = useState<IndiceSeccion>();
  const [anioUrl, setAnio] = useParametro("anio");
  const [datosAnio, setDatosAnio] = useState<Indicador[]>([]);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [distrito, setDistrito] = useParametro("distrito");
  const [serie, setSerie] = useState<Indicador[]>([]);
  const [verTabla, setVerTabla] = useState(false);

  useEffect(() => {
    cargar<IndiceSeccion>("indicadores/empleo/indice.json").then(setIndice);
  }, []);

  // Lo que viene en la URL se valida; si no sirve, se usa el valor por defecto.
  const anio = anioUrl && indice?.anios.includes(anioUrl) ? anioUrl : indice?.anios.at(-1);
  const metrica = METRICAS.find((m) => m.clave === metricaUrl)?.clave ?? "empleos_formales";

  useEffect(() => {
    if (!anio) return;
    cargar<ArchivoIndicadores>(`indicadores/empleo/anio_${anio}.json`).then((a) => setDatosAnio(a.indicadores));
  }, [anio]);

  useEffect(() => {
    const ruta = distrito ? `serie_distrito_${distrito}` : "serie_municipio_MSP";
    cargar<ArchivoIndicadores>(`indicadores/empleo/${ruta}.json`).then((a) => setSerie(a.indicadores));
  }, [distrito]);

  const delDistrito = useMemo(
    () => datosAnio.filter((i) => i.nivel === "distrito" && claveIndicador(i) === metrica),
    [datosAnio, metrica],
  );
  const valores = useMemo(
    () => Object.fromEntries(delDistrito.map((i) => [i.codigo_territorio, i.valor])),
    [delDistrito],
  );
  const ranking = useMemo(() => delDistrito.filter(tieneValor).sort((a, b) => b.valor - a.valor), [delDistrito]);
  const unidad = delDistrito[0]?.unidad ?? "";
  const etiquetaMetrica = METRICAS.find((m) => m.clave === metrica)!.etiqueta;

  const territorio = distrito ?? "MSP";
  const busca = (clave: string) =>
    datosAnio.find((i) => i.codigo_territorio === territorio && claveIndicador(i) === clave);
  const nombreTerritorio = busca("empleos_formales")?.nombre_territorio ?? "Município de São Paulo";

  // El municipio no tiene participación ni densidad: su serie usa el total de empleos.
  const metricaSerie = distrito || metrica === "establecimientos_formales" ? metrica : "empleos_formales";
  const etiquetaSerie = METRICAS.find((m) => m.clave === metricaSerie)!.etiqueta;
  const serieMetrica = serie
    .filter((i) => claveIndicador(i) === metricaSerie)
    .map((i) => ({ anio: i.vigencia, valor: i.valor }));
  const unidadSerie = serie.find((i) => claveIndicador(i) === metricaSerie)?.unidad;

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

      <div className="filtros">
        <label>
          Año
          <select value={anio} onChange={(e) => setAnio(e.target.value)}>
            {indice?.anios.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>
        <label>
          Indicador
          <select value={metrica} onChange={(e) => setMetrica(e.target.value as typeof metrica)}>
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
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>
            {etiquetaMetrica} por distrito, {anio}
          </h2>
          <MapaDistritos valores={valores} unidad={unidad} seleccionado={distrito} onSeleccionar={setDistrito} />
        </div>

        <div className="panel">
          <div className="panel-cabecera">
            <h2>Los 10 distritos con más {etiquetaMetrica.toLowerCase()}</h2>
            <button type="button" className="enlace" onClick={() => setVerTabla((v) => !v)}>
              {verTabla ? "Ver gráfico" : "Ver tabla de los 96"}
            </button>
          </div>
          {verTabla ? (
            <div className="tabla-scroll">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Distrito</th>
                    <th className="num">{unidad}</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((i, n) => (
                    <tr key={i.id} className={i.codigo_territorio === distrito ? "fila-activa" : ""}>
                      <td>{n + 1}</td>
                      <td>
                        <button type="button" className="enlace" onClick={() => setDistrito(i.codigo_territorio)}>
                          {i.nombre_territorio}
                        </button>
                      </td>
                      <td className="num">{formatear(i.valor, i.unidad)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={360}>
              <BarChart
                data={ranking
                  .slice(0, 10)
                  .map((i) => ({ nombre: i.nombre_territorio, valor: i.valor, codigo: i.codigo_territorio }))}
                layout="vertical"
                margin={{ left: 8, right: 16 }}
                barCategoryGap={4}
              >
                <CartesianGrid horizontal={false} stroke="var(--grilla)" />
                <XAxis type="number" tickFormatter={formatearCorto} stroke="var(--texto-tenue)" fontSize={12} />
                <YAxis type="category" dataKey="nombre" width={120} stroke="var(--texto-tenue)" fontSize={12} />
                <Tooltip
                  cursor={{ fill: "var(--superficie-2)" }}
                  formatter={(v) => [formatear(Number(v), unidad), unidad]}
                  contentStyle={{ background: "var(--superficie)", border: "1px solid var(--borde)", borderRadius: 8 }}
                  itemStyle={{ color: "var(--texto)" }}
                  labelStyle={{ color: "var(--texto-2)" }}
                />
                <Bar
                  dataKey="valor"
                  fill={AZUL}
                  radius={[0, 4, 4, 0]}
                  onClick={(d) => setDistrito((d as unknown as { codigo: string }).codigo)}
                  style={{ cursor: "pointer" }}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
          <p className="nota">Excluye las filas «inválidos» y «no localizados», que se conservan en el lago.</p>
        </div>
      </div>

      <div className="panel">
        <h2>
          {etiquetaSerie} en {nombreTerritorio}, 2011-2024
        </h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={serieMetrica} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid vertical={false} stroke="var(--grilla)" />
            <XAxis dataKey="anio" stroke="var(--texto-tenue)" fontSize={12} />
            <YAxis tickFormatter={formatearCorto} stroke="var(--texto-tenue)" fontSize={12} width={60} />
            <ReferenceLine
              x="2022"
              stroke="var(--texto-tenue)"
              strokeDasharray="4 4"
              label={{ value: "Quiebre RAIS", fontSize: 11, fill: "var(--texto-tenue)", position: "insideTopLeft" }}
            />
            <Tooltip
              formatter={(v) => [formatear(Number(v), unidadSerie), etiquetaSerie]}
              contentStyle={{ background: "var(--superficie)", border: "1px solid var(--borde)", borderRadius: 8 }}
              itemStyle={{ color: "var(--texto)" }}
              labelStyle={{ color: "var(--texto-2)" }}
            />
            <Line
              dataKey="valor"
              stroke={AZUL}
              strokeWidth={2}
              dot={{ r: 4, fill: AZUL, strokeWidth: 2, stroke: "var(--superficie)" }}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="nota">
          Desde 2022 la RAIS cambió la forma de captar los datos (nota técnica del MTE): los saltos alrededor de ese
          año, como el de Brás en 2022, pueden ser del registro y no de la economía.
        </p>
      </div>

      <aside className="limitacion">
        <strong>Lo que esta sección no muestra todavía:</strong> empleo por sexo (F13-F15), por raza o color (F16-F17,
        solo como porcentaje), centros comerciales (F22-F24) y área residencial (F28). El lago no tiene empleo por
        sector económico.
      </aside>
    </section>
  );
}
