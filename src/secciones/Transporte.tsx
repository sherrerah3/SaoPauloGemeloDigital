import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import CodigoPregunta from "../componentes/CodigoPregunta";
import { EJE, ESTILO_TOOLTIP, SERIE_1 } from "../componentes/graficos";
import MapaDistritos from "../componentes/MapaDistritos";
import RankingDistritos from "../componentes/RankingDistritos";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import {
  type ArchivoIndicadores,
  cargar,
  claveIndicador,
  formatear,
  formatearCorto,
  type Indicador,
  metricaPorTerritorio,
} from "../datos";
import { useParametro } from "../rutas";

// «orden» decide el ranking: en cobertura interesa dónde falta, en densidad dónde sobra.
const METRICAS = [
  { grupo: "Transporte", clave: "cobertura_poblacion", etiqueta: "Población cubierta (bus o metro)", orden: "asc" },
  { grupo: "Transporte", clave: "cobertura_poblacion_metro", etiqueta: "Población cubierta por metro", orden: "desc" },
  { grupo: "Transporte", clave: "cobertura_area", etiqueta: "Área cubierta (bus o metro)", orden: "asc" },
  { grupo: "Transporte", clave: "paradas_por_km2", etiqueta: "Paradas de bus por km²", orden: "asc" },
  { grupo: "Transporte", clave: "km_red_bus_por_km2", etiqueta: "Red de bus por km²", orden: "asc" },
  { grupo: "Transporte", clave: "lineas_bus", etiqueta: "Líneas de bus que pasan", orden: "desc" },
  { grupo: "Transporte", clave: "estaciones_metro", etiqueta: "Estaciones de metro", orden: "desc" },
  { grupo: "Transporte", clave: "densidad", etiqueta: "Densidad de población", orden: "desc" },
  {
    grupo: "Equipamientos",
    clave: "escuelas_infantil_por_10mil",
    etiqueta: "Escuelas infantiles por 10 mil hab.",
    orden: "asc",
  },
  {
    grupo: "Equipamientos",
    clave: "escuelas_basica_por_10mil",
    etiqueta: "Escuelas básicas por 10 mil hab.",
    orden: "asc",
  },
  { grupo: "Equipamientos", clave: "ferias_por_10mil", etiqueta: "Ferias libres por 10 mil hab.", orden: "asc" },
  { grupo: "Equipamientos", clave: "mercados", etiqueta: "Mercados y sacolões municipales", orden: "desc" },
  { grupo: "Equipamientos", clave: "centros_deportivos", etiqueta: "Centros deportivos", orden: "desc" },
  { grupo: "Equipamientos", clave: "shoppings", etiqueta: "Shoppings", orden: "desc" },
  { grupo: "Equipamientos", clave: "abl_shoppings", etiqueta: "Área de shoppings (ABL)", orden: "desc" },
] as const;
type Clave = (typeof METRICAS)[number]["clave"];
const GRUPOS = ["Transporte", "Equipamientos"] as const;

interface ArchivoPasajeros extends ArchivoIndicadores {
  meses: string[];
  radio_cobertura_m: number;
}

export default function Transporte() {
  const [datos, setDatos] = useState<Indicador[]>([]);
  const [radio, setRadio] = useState<number>();
  const [pasajeros, setPasajeros] = useState<ArchivoPasajeros | null>(null);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [distrito, setDistrito] = useParametro("distrito");
  const metrica: Clave = METRICAS.find((m) => m.clave === metricaUrl)?.clave ?? "cobertura_poblacion";

  useEffect(() => {
    const transporte = cargar<ArchivoIndicadores & { radio_cobertura_m: number }>(
      "indicadores/transporte/distritos.json",
    );
    const equipamientos = cargar<ArchivoIndicadores>("indicadores/equipamientos/distritos.json");
    Promise.all([transporte, equipamientos]).then(([t, e]) => {
      setDatos([...t.indicadores, ...e.indicadores]);
      setRadio(t.radio_cobertura_m);
    });
    cargar<ArchivoPasajeros>("indicadores/transporte/pasajeros.json")
      .then(setPasajeros)
      .catch(() => setPasajeros(null));
  }, []);

  const def = METRICAS.find((m) => m.clave === metrica)!;
  const { valores, ranking, unidad } = useMemo(
    () => metricaPorTerritorio(datos, metrica, def.orden),
    [datos, metrica, def.orden],
  );

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
        <p className="rotulo-pregunta">
          <CodigoPregunta codigo="P1" /> Pregunta 1
        </p>
        <h1>¿Qué tan cubierta está la ciudad por transporte público?</h1>
        <p className="entrada">
          Paradas de bus, líneas y estaciones de metro de GeoSampa cruzadas con la población del censo 2022 en los 96
          distritos. Un habitante está «cubierto» si vive a {radio ?? "…"} m o menos, en línea recta, de una parada o
          estación. Haz clic en un distrito para ver sus cifras.
        </p>
      </header>

      <div className="filtros">
        <label>
          Indicador
          <select value={metrica} onChange={(e) => setMetrica(e.target.value as Clave)}>
            {GRUPOS.map((grupo) => (
              <optgroup key={grupo} label={grupo}>
                {METRICAS.filter((m) => m.grupo === grupo).map((m) => (
                  <option key={m.clave} value={m.clave}>
                    {m.etiqueta}
                  </option>
                ))}
              </optgroup>
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
          titulo={`Población cubierta en ${nombreTerritorio}`}
          indicador={busca("cobertura_poblacion")}
          destacado
        />
        <TarjetaIndicador titulo="Población cubierta solo por metro" indicador={busca("cobertura_poblacion_metro")} />
        <TarjetaIndicador titulo="Paradas de bus" indicador={busca("paradas_bus")} />
        <TarjetaIndicador titulo="Estaciones de metro" indicador={busca("estaciones_metro")} />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>{def.etiqueta} por distrito</h2>
          <MapaDistritos valores={valores} unidad={unidad} seleccionado={distrito} onSeleccionar={setDistrito} />
        </div>

        <RankingDistritos
          titulo={`Los 10 distritos con ${def.orden === "asc" ? "menor" : "mayor"} ${def.etiqueta.toLowerCase()}`}
          ranking={ranking}
          unidad={unidad}
          seleccionado={distrito}
          onSeleccionar={setDistrito}
        >
          {distrito && (
            <div className="rejilla-mini">
              <TarjetaIndicador titulo="Población" indicador={busca("poblacion")} />
              <TarjetaIndicador titulo="Área cubierta" indicador={busca("cobertura_area")} />
            </div>
          )}
        </RankingDistritos>
      </div>

      <h2 className="subtitulo">Equipamientos en {nombreTerritorio}</h2>
      <div className="rejilla-tarjetas">
        <TarjetaIndicador titulo="Escuelas públicas de educación infantil" indicador={busca("escuelas_infantil")} />
        <TarjetaIndicador titulo="Escuelas públicas fundamental y media" indicador={busca("escuelas_basica")} />
        <TarjetaIndicador titulo="Ferias libres" indicador={busca("ferias")} />
        <TarjetaIndicador titulo="Shoppings" indicador={busca("shoppings")} />
      </div>

      {pasajeros && (
        <div className="rejilla-dos">
          <div className="panel">
            <h2>Pasajeros por mes en los buses municipales</h2>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={serieMensual} margin={{ left: 8, right: 16, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--grilla)" />
                <XAxis dataKey="mes" {...EJE} />
                <YAxis tickFormatter={formatearCorto} width={60} {...EJE} />
                <Tooltip formatter={(v) => [formatear(Number(v)), "Pasajeros"]} {...ESTILO_TOOLTIP} />
                <Line
                  dataKey="valor"
                  stroke={SERIE_1}
                  strokeWidth={2}
                  dot={{ r: 4, fill: SERIE_1, strokeWidth: 2, stroke: "var(--superficie)" }}
                />
              </LineChart>
            </ResponsiveContainer>
            <p className="nota">
              Fuente F05 (SPTrans). Suma de los reportes diarios; un mes al que le falta algún día en el portal se
              completa con el consolidado mensual de SPTrans. No se reparte por distrito porque la fuente no tiene
              geografía.
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
                <XAxis type="number" tickFormatter={formatearCorto} {...EJE} />
                <YAxis type="category" dataKey="nombre" width={190} stroke="var(--texto-tenue)" fontSize={11} />
                <Tooltip
                  cursor={{ fill: "var(--superficie-2)" }}
                  formatter={(v) => [formatear(Number(v)), "Pasajeros"]}
                  {...ESTILO_TOOLTIP}
                />
                <Bar dataKey="valor" fill={SERIE_1} radius={[0, 4, 4, 0]} />
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
        capa «estacao_trem», pero no están en el catálogo), buses en tiempo real (F09, fuera del lago) y museos (F38,
        descartada por el equipo). Los pasajeros de 2023 y 2024 no aparecen en el portal de SPTrans con la misma ruta
        que 2025-2026. Los equipamientos se cuentan donde están, no a qué distancia caminando quedan.
      </aside>
    </section>
  );
}
