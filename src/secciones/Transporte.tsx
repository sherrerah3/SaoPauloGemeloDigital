import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import MapaDistritos from "../componentes/MapaDistritos";
import { cargar, claveIndicador, formatear, formatearCorto, type ArchivoIndicadores, type Indicador } from "../datos";

// «orden» decide el ranking: en cobertura interesa dónde falta, en densidad dónde sobra.
const METRICAS = [
  { clave: "cobertura_poblacion", etiqueta: "Población cubierta (bus o metro)", orden: "asc" },
  { clave: "cobertura_poblacion_metro", etiqueta: "Población cubierta por metro", orden: "desc" },
  { clave: "cobertura_area", etiqueta: "Área cubierta (bus o metro)", orden: "asc" },
  { clave: "paradas_por_km2", etiqueta: "Paradas de bus por km²", orden: "asc" },
  { clave: "km_red_bus_por_km2", etiqueta: "Red de bus por km²", orden: "asc" },
  { clave: "lineas_bus", etiqueta: "Líneas de bus que pasan", orden: "desc" },
  { clave: "estaciones_metro", etiqueta: "Estaciones de metro", orden: "desc" },
  { clave: "densidad", etiqueta: "Densidad de población", orden: "desc" },
] as const;
type Clave = (typeof METRICAS)[number]["clave"];

const ESTILO_TOOLTIP = {
  contentStyle: { background: "var(--superficie)", border: "1px solid var(--borde)", borderRadius: 8 },
  itemStyle: { color: "var(--texto)" },
  labelStyle: { color: "var(--texto-2)" },
};
const AZUL = "var(--serie-1)";

interface ArchivoPasajeros extends ArchivoIndicadores {
  meses: string[];
  radio_cobertura_m: number;
}

export default function Transporte() {
  const [datos, setDatos] = useState<Indicador[]>([]);
  const [radio, setRadio] = useState<number>();
  const [pasajeros, setPasajeros] = useState<ArchivoPasajeros | null>(null);
  const [metrica, setMetrica] = useState<Clave>("cobertura_poblacion");
  const [distrito, setDistrito] = useState<string | null>(null);
  const [verTabla, setVerTabla] = useState(false);

  useEffect(() => {
    cargar<ArchivoIndicadores & { radio_cobertura_m: number }>("indicadores/transporte/distritos.json").then((a) => {
      setDatos(a.indicadores);
      setRadio(a.radio_cobertura_m);
    });
    cargar<ArchivoPasajeros>("indicadores/transporte/pasajeros.json")
      .then(setPasajeros)
      .catch(() => setPasajeros(null));
  }, []);

  const def = METRICAS.find((m) => m.clave === metrica)!;
  const delDistrito = useMemo(
    () => datos.filter((i) => i.nivel === "distrito" && claveIndicador(i) === metrica),
    [datos, metrica],
  );
  const valores = useMemo(() => Object.fromEntries(delDistrito.map((i) => [i.codigo_territorio, i.valor])), [delDistrito]);
  const ranking = useMemo(
    () =>
      [...delDistrito]
        .filter((i) => i.valor !== null)
        .sort((a, b) => (def.orden === "asc" ? a.valor! - b.valor! : b.valor! - a.valor!)),
    [delDistrito, def.orden],
  );
  const unidad = delDistrito[0]?.unidad ?? "";

  const territorio = distrito ?? "MSP";
  const busca = (clave: string) => datos.find((i) => i.codigo_territorio === territorio && claveIndicador(i) === clave);
  const nombreTerritorio = busca("poblacion")?.nombre_territorio ?? "Município de São Paulo";

  const serieMensual = (pasajeros?.indicadores ?? [])
    .filter((i) => claveIndicador(i) === "pasajeros_total_mes")
    .map((i) => ({ mes: i.vigencia, valor: i.valor }));
  const lineas = (pasajeros?.indicadores ?? []).filter((i) => i.nivel === "linea").slice(0, 15);
  const meses = pasajeros?.meses ?? [];

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <p className="antetitulo">Pregunta P1</p>
        <h1>¿Qué tan cubierta está la ciudad por transporte público?</h1>
        <p className="entrada">
          Paradas de bus, líneas y estaciones de metro de GeoSampa cruzadas con la población del censo 2022 en los 96
          distritos. Un habitante está «cubierto» si vive a {radio ?? "…"} m o menos, en línea recta, de una parada o
          estación. Haz clic en un distrito para ver sus cifras.
        </p>
      </header>

      <div className="filtros" role="group" aria-label="Filtros">
        <label>
          Indicador
          <select value={metrica} onChange={(e) => setMetrica(e.target.value as Clave)}>
            {METRICAS.map((m) => (
              <option key={m.clave} value={m.clave}>
                {m.etiqueta}
              </option>
            ))}
          </select>
        </label>
        {distrito && (
          <button className="boton-secundario" onClick={() => setDistrito(null)}>
            Volver al municipio
          </button>
        )}
      </div>

      <div className="rejilla-tarjetas">
        <TarjetaIndicador titulo={`Población cubierta · ${nombreTerritorio}`} indicador={busca("cobertura_poblacion")} destacado />
        <TarjetaIndicador titulo="Población cubierta solo por metro" indicador={busca("cobertura_poblacion_metro")} />
        <TarjetaIndicador titulo="Paradas de bus" indicador={busca("paradas_bus")} />
        <TarjetaIndicador titulo="Estaciones de metro" indicador={busca("estaciones_metro")} />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>{def.etiqueta} por distrito</h2>
          <MapaDistritos valores={valores} unidad={unidad} seleccionado={distrito} onSeleccionar={setDistrito} />
        </div>

        <div className="panel">
          <div className="panel-cabecera">
            <h2>
              Los 10 distritos con {def.orden === "asc" ? "menor" : "mayor"} {def.etiqueta.toLowerCase()}
            </h2>
            <button className="enlace" onClick={() => setVerTabla((v) => !v)}>
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
                        <button className="enlace" onClick={() => setDistrito(i.codigo_territorio)}>
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
                data={ranking.slice(0, 10).map((i) => ({ nombre: i.nombre_territorio, valor: i.valor, codigo: i.codigo_territorio }))}
                layout="vertical"
                margin={{ left: 8, right: 16 }}
                barCategoryGap={4}
              >
                <CartesianGrid horizontal={false} stroke="var(--grilla)" />
                <XAxis type="number" tickFormatter={formatearCorto} stroke="var(--texto-tenue)" fontSize={12} />
                <YAxis type="category" dataKey="nombre" width={130} stroke="var(--texto-tenue)" fontSize={12} />
                <Tooltip cursor={{ fill: "var(--superficie-2)" }} formatter={(v) => [formatear(Number(v), unidad), unidad]} {...ESTILO_TOOLTIP} />
                <Bar
                  dataKey="valor"
                  fill={AZUL}
                  radius={[0, 4, 4, 0]}
                  onClick={(d) => setDistrito((d as unknown as { codigo: string }).codigo)}
                  style={{ cursor: "pointer" }}
                >
                  {/* Con coberturas cercanas al 100 % las barras se parecen: el valor va escrito. */}
                  <LabelList
                    dataKey="valor"
                    position="insideRight"
                    formatter={(v: unknown) => formatear(Number(v), unidad)}
                    style={{ fill: "#ffffff", fontSize: 11, fontWeight: 600 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {distrito && (
            <div className="rejilla-mini">
              <TarjetaIndicador titulo="Población" indicador={busca("poblacion")} />
              <TarjetaIndicador titulo="Área cubierta" indicador={busca("cobertura_area")} />
            </div>
          )}
        </div>
      </div>

      {pasajeros && (
        <div className="rejilla-dos">
          <div className="panel">
            <h2>Pasajeros transportados por mes · buses municipales</h2>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={serieMensual} margin={{ left: 8, right: 16, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--grilla)" />
                <XAxis dataKey="mes" stroke="var(--texto-tenue)" fontSize={12} />
                <YAxis tickFormatter={formatearCorto} stroke="var(--texto-tenue)" fontSize={12} width={60} />
                <Tooltip formatter={(v) => [formatear(Number(v)), "Pasajeros"]} {...ESTILO_TOOLTIP} />
                <Line dataKey="valor" stroke={AZUL} strokeWidth={2} dot={{ r: 4, fill: AZUL, strokeWidth: 2, stroke: "var(--superficie)" }} />
              </LineChart>
            </ResponsiveContainer>
            <p className="nota">
              F05 · SPTrans. Suma de los reportes diarios; un mes al que le falta algún día en el portal se completa
              con el consolidado mensual de SPTrans. No se reparte por distrito porque la fuente no tiene geografía.
            </p>
          </div>
          <div className="panel">
            <h2>Las 15 líneas con más pasajeros</h2>
            <ResponsiveContainer width="100%" height={420}>
              <BarChart
                data={lineas.map((i) => ({ nombre: `${i.codigo_territorio} ${i.nombre_territorio}`, valor: i.valor }))}
                layout="vertical"
                margin={{ left: 8, right: 16 }}
                barCategoryGap={3}
              >
                <CartesianGrid horizontal={false} stroke="var(--grilla)" />
                <XAxis type="number" tickFormatter={formatearCorto} stroke="var(--texto-tenue)" fontSize={12} />
                <YAxis type="category" dataKey="nombre" width={190} stroke="var(--texto-tenue)" fontSize={11} />
                <Tooltip cursor={{ fill: "var(--superficie-2)" }} formatter={(v) => [formatear(Number(v)), "Pasajeros"]} {...ESTILO_TOOLTIP} />
                <Bar dataKey="valor" fill={AZUL} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="nota">
              Total de {meses[0]} a {meses[meses.length - 1]} ({meses.length} meses completos).
            </p>
          </div>
        </div>
      )}

      <aside className="limitacion">
        <strong>Lo que esta sección no muestra todavía:</strong> estaciones de tren CPTM (GeoSampa las publica en la
        capa «estacao_trem», pero no están en el catálogo: candidata a F42), equipamientos (mercados F21, deporte
        F33-F34, escuelas F39-F40) y buses en tiempo real (F09, fuera del lago). Los pasajeros de 2023 y 2024 no
        aparecen en el portal de SPTrans con la misma ruta que 2025-2026.
      </aside>
    </section>
  );
}
