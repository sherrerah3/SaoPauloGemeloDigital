import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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
  metricaPorTerritorio,
} from "../datos";
import { useParametro } from "../rutas";

const METRICAS = [
  { clave: "densidad", etiqueta: "Densidad de población" },
  { clave: "poblacion", etiqueta: "Población" },
  { clave: "domicilios_favela_pct", etiqueta: "Domicilios en favelas" },
  { clave: "domicilios_favela", etiqueta: "Domicilios en favelas (número)" },
  { clave: "area_favela_pct", etiqueta: "Área ocupada por favelas" },
  { clave: "favelas", etiqueta: "Favelas" },
] as const;
type Clave = (typeof METRICAS)[number]["clave"];

// La población y la densidad (F41) ya se publican con transporte; aquí se reutilizan.
const DE_TRANSPORTE = new Set(["poblacion", "densidad"]);

// Población histórica (F01): los cuatro territorios que trae la fuente, de menor a mayor.
const TERRITORIOS_HISTORIA = [
  { nivel: "municipio", etiqueta: "Município de São Paulo" },
  { nivel: "region_metropolitana", etiqueta: "Región Metropolitana de São Paulo" },
  { nivel: "estado", etiqueta: "Estado de São Paulo" },
  { nivel: "pais", etiqueta: "Brasil" },
] as const;

// IDH municipal (F07): solo existen estos dos censos.
const ANIOS_IDH = ["2010", "2000"];
const METRICAS_IDH = [
  { clave: "idhm", etiqueta: "IDHM" },
  { clave: "idhm_renda", etiqueta: "IDHM Renda" },
] as const;

// Nacimientos (F18-F20). 2023 es el único año casi completo: en 2024 y 2025 una parte de los nacimientos
// viene sin distrito (ver la tarjeta «Sin distrito conocido»), así que es el que se muestra al abrir.
const ANIOS_NACIMIENTOS = ["2025", "2024", "2023"];
const ANIO_NACIMIENTOS_INICIAL = "2023";
const METRICAS_NACIMIENTOS = [
  { clave: "nacidos_vivos_por_mil_hab", etiqueta: "Nacimientos por mil habitantes" },
  { clave: "nacidos_vivos", etiqueta: "Nacimientos" },
] as const;

export default function Gente() {
  const [datos, setDatos] = useState<Indicador[]>([]);
  const [area, setArea] = useState<Indicador[]>([]);
  const [historia, setHistoria] = useState<Indicador[]>([]);
  const [idh, setIdh] = useState<Indicador[]>([]);
  const [nacimientos, setNacimientos] = useState<Indicador[]>([]);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [distrito, setDistrito] = useParametro("distrito");
  const [historiaUrl, setHistoriaTerritorio] = useParametro("historia");
  const [anioIdhUrl, setAnioIdh] = useParametro("anio_idh");
  const [metricaIdhUrl, setMetricaIdh] = useParametro("metrica_idh");
  const [subprefeitura, setSubprefeitura] = useParametro("subprefeitura");
  const [anioNacUrl, setAnioNac] = useParametro("anio_nac");
  const [metricaNacUrl, setMetricaNac] = useParametro("metrica_nac");
  const def = METRICAS.find((m) => m.clave === metricaUrl) ?? METRICAS[0];
  const metrica: Clave = def.clave;
  const territorioHistoria = TERRITORIOS_HISTORIA.find((t) => t.nivel === historiaUrl) ?? TERRITORIOS_HISTORIA[0];
  const defIdh = METRICAS_IDH.find((m) => m.clave === metricaIdhUrl) ?? METRICAS_IDH[0];
  const anioIdh = anioIdhUrl && ANIOS_IDH.includes(anioIdhUrl) ? anioIdhUrl : ANIOS_IDH[0];
  const defNac = METRICAS_NACIMIENTOS.find((m) => m.clave === metricaNacUrl) ?? METRICAS_NACIMIENTOS[0];
  const anioNac = anioNacUrl && ANIOS_NACIMIENTOS.includes(anioNacUrl) ? anioNacUrl : ANIO_NACIMIENTOS_INICIAL;

  useEffect(() => {
    const gente = cargar<ArchivoIndicadores>("indicadores/gente/distritos.json");
    const transporte = cargar<ArchivoIndicadores>("indicadores/transporte/distritos.json");
    Promise.all([gente, transporte]).then(([g, t]) =>
      setDatos([...g.indicadores, ...t.indicadores.filter((i) => DE_TRANSPORTE.has(claveIndicador(i)))]),
    );
    cargar<ArchivoIndicadores>("indicadores/gente/area_construida.json").then((a) => setArea(a.indicadores));
    cargar<ArchivoIndicadores>("indicadores/gente/poblacion_historica.json").then((a) => setHistoria(a.indicadores));
    cargar<ArchivoIndicadores>("indicadores/gente/idhm.json").then((a) => setIdh(a.indicadores));
    cargar<ArchivoIndicadores>("indicadores/gente/nacimientos.json").then((a) => setNacimientos(a.indicadores));
  }, []);

  const { valores, ranking, unidad } = useMemo(() => metricaPorTerritorio(datos, metrica), [datos, metrica]);

  const territorio = distrito ?? "MSP";
  const busca = (clave: string) => datos.find((i) => i.codigo_territorio === territorio && claveIndicador(i) === clave);
  const nombreTerritorio = busca("poblacion")?.nombre_territorio ?? "Município de São Paulo";
  const serieArea = area.map((i) => ({ anio: i.vigencia, valor: i.valor }));

  // Población histórica: un punto por censo; los censos no son anuales, así que el eje X es numérico.
  const censos = useMemo(
    () =>
      historia
        .filter((i) => i.nivel === territorioHistoria.nivel)
        .sort((a, b) => Number(a.vigencia) - Number(b.vigencia)),
    [historia, territorioHistoria],
  );
  const serieHistoria = censos.map((i) => ({ anio: Number(i.vigencia), valor: i.valor }));

  // IDHM: un año a la vez, por subprefeitura (la fuente las llama Prefeituras Regionais).
  const idhDelAnio = useMemo(() => idh.filter((i) => i.vigencia === anioIdh), [idh, anioIdh]);
  const idhMapa = useMemo(
    () => metricaPorTerritorio(idhDelAnio, defIdh.clave, "desc", "subprefeitura"),
    [idhDelAnio, defIdh],
  );
  const territorioIdh = subprefeitura ?? "MSP";
  const buscaIdh = (clave: string) =>
    idhDelAnio.find((i) => i.codigo_territorio === territorioIdh && claveIndicador(i) === clave);
  const nombreIdh = buscaIdh("idhm")?.nombre_territorio ?? "Município de São Paulo";

  // Nacimientos: el mapa y el ranking van por distrito; las tarjetas siguen al distrito elegido arriba.
  const nacDelAnio = useMemo(() => nacimientos.filter((i) => i.vigencia === anioNac), [nacimientos, anioNac]);
  const nacMapa = useMemo(() => metricaPorTerritorio(nacDelAnio, defNac.clave), [nacDelAnio, defNac]);
  const buscaNac = (clave: string, codigo = territorio) =>
    nacDelAnio.find((i) => i.codigo_territorio === codigo && claveIndicador(i) === clave);

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <h1>¿Dónde vive la gente?</h1>
        <p className="entrada">
          Población y densidad del censo 2022, las favelas que delimita la Secretaría de Vivienda (HABITASAMPA), la
          población desde 1872, el IDH municipal de 2000 y 2010 y los nacimientos de 2023 a 2025. En el mapa 3D cada
          favela muestra su nombre, pero no su calle.
        </p>
      </header>

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
        <TarjetaIndicador titulo={`Población en ${nombreTerritorio}`} indicador={busca("poblacion")} destacado />
        <TarjetaIndicador titulo="Densidad" indicador={busca("densidad")} />
        <TarjetaIndicador titulo="Domicilios en favelas" indicador={busca("domicilios_favela_pct")} />
        <TarjetaIndicador titulo="Favelas" indicador={busca("favelas")} />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>{def.etiqueta} por distrito</h2>
          <MapaDistritos valores={valores} unidad={unidad} seleccionado={distrito} onSeleccionar={setDistrito} />
        </div>
        <RankingDistritos
          titulo={`Los 10 distritos con más ${def.etiqueta.toLowerCase()}`}
          ranking={ranking}
          unidad={unidad}
          seleccionado={distrito}
          onSeleccionar={setDistrito}
        />
      </div>

      <div className="panel">
        <h2>
          Área construida residencial de la ciudad, {serieArea[0]?.anio}-{serieArea.at(-1)?.anio}
        </h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={serieArea} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid vertical={false} stroke="var(--grilla)" />
            <XAxis dataKey="anio" {...EJE} />
            <YAxis tickFormatter={formatearCorto} width={60} unit=" km²" {...EJE} />
            <Tooltip formatter={(v) => [`${formatear(Number(v))} km²`, "Área residencial"]} {...ESTILO_TOOLTIP} />
            <Line dataKey="valor" stroke={SERIE_1} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
        <p className="nota">
          Fuente F28 (catastro del IPTU, Infocidade). Superficie construida de uso residencial registrada en enero de
          cada año, para toda la ciudad: la fuente no la abre por distrito.
        </p>
      </div>

      <header className="seccion-cabecera">
        <h2 className="subtitulo-seccion">¿Cuánto ha crecido la población?</h2>
        <p className="entrada">
          Población de cada censo desde 1872, que reúne la Prefeitura con datos del IBGE, para la ciudad, la Región
          Metropolitana, el Estado y Brasil.
        </p>
      </header>

      <div className="filtros">
        <label>
          Territorio
          <select value={territorioHistoria.nivel} onChange={(e) => setHistoriaTerritorio(e.target.value)}>
            {TERRITORIOS_HISTORIA.map((t) => (
              <option key={t.nivel} value={t.nivel}>
                {t.etiqueta}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="rejilla-tarjetas">
        <TarjetaIndicador
          titulo={`Último censo (${censos.at(-1)?.vigencia ?? "…"})`}
          indicador={censos.at(-1)}
          destacado
        />
        <TarjetaIndicador titulo={`Primer censo con dato (${censos[0]?.vigencia ?? "…"})`} indicador={censos[0]} />
      </div>

      <div className="panel">
        <h2>Población de {territorioHistoria.etiqueta} en cada censo</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={serieHistoria} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid vertical={false} stroke="var(--grilla)" />
            <XAxis dataKey="anio" type="number" domain={["dataMin", "dataMax"]} {...EJE} />
            <YAxis tickFormatter={formatearCorto} width={64} {...EJE} />
            <Tooltip
              formatter={(v) => [`${formatear(Number(v))} personas`, "Población"]}
              labelFormatter={(anio) => `Censo de ${anio}`}
              {...ESTILO_TOOLTIP}
            />
            <Line dataKey="valor" stroke={SERIE_1} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
        <p className="nota">
          Fuente F01 (censos del IBGE, Infocidade). Cada punto es un censo: no hay cifras de los años intermedios.
        </p>
      </div>

      <header className="seccion-cabecera">
        <h2 className="subtitulo-seccion">¿Qué tan desarrollada está cada zona?</h2>
        <p className="entrada">
          Índice de Desarrollo Humano Municipal (IDHM) de cada subprefeitura, con la dimensión de ingreso. Haz clic en
          una subprefeitura para ver sus cifras.
        </p>
      </header>

      <SelectorAnio etiqueta="Año del censo" anios={ANIOS_IDH} valor={anioIdh} onCambiar={setAnioIdh} />

      <div className="filtros">
        <label>
          Indicador
          <select value={defIdh.clave} onChange={(e) => setMetricaIdh(e.target.value)}>
            {METRICAS_IDH.map((m) => (
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
        <TarjetaIndicador titulo={`IDHM en ${nombreIdh}`} indicador={buscaIdh("idhm")} destacado />
        <TarjetaIndicador titulo="IDHM Renda" indicador={buscaIdh("idhm_renda")} />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>
            {defIdh.etiqueta} por subprefeitura, {anioIdh}
          </h2>
          <MapaDistritos
            nivel="subprefeitura"
            valores={idhMapa.valores}
            unidad={idhMapa.unidad}
            seleccionado={subprefeitura}
            onSeleccionar={setSubprefeitura}
          />
        </div>
        <RankingDistritos
          titulo={`Las 10 subprefeituras con mayor ${defIdh.etiqueta}`}
          ranking={idhMapa.ranking}
          unidad={idhMapa.unidad}
          seleccionado={subprefeitura}
          onSeleccionar={setSubprefeitura}
          columna="Subprefeitura"
        />
      </div>

      <aside className="limitacion">
        <strong>Antes de usar el IDHM:</strong> son cifras de los censos de 2000 y 2010, así que no muestran cómo está
        cada zona hoy. La fuente trae 31 prefeituras regionales: Sapopemba, que desde 2013 es una subprefeitura aparte,
        está dentro de Vila Prudente y aparece sin dato en el mapa.
      </aside>

      <header className="seccion-cabecera">
        <h2 className="subtitulo-seccion">¿Cuántos bebés nacen y dónde?</h2>
        <p className="entrada">
          Nacidos vivos por distrito y año, del Sistema de Información sobre Nacidos Vivos (SINASC) de la Secretaría de
          Salud, y su tasa por mil habitantes. Haz clic en un distrito para ver sus cifras.
        </p>
      </header>

      <SelectorAnio
        etiqueta="Año de los nacimientos"
        anios={ANIOS_NACIMIENTOS}
        valor={anioNac}
        onCambiar={setAnioNac}
      />

      <div className="filtros">
        <label>
          Indicador
          <select value={defNac.clave} onChange={(e) => setMetricaNac(e.target.value)}>
            {METRICAS_NACIMIENTOS.map((m) => (
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
          titulo={`Nacimientos en ${buscaNac("nacidos_vivos")?.nombre_territorio ?? nombreTerritorio}`}
          indicador={buscaNac("nacidos_vivos")}
          destacado
        />
        <TarjetaIndicador titulo="Nacimientos por mil habitantes" indicador={buscaNac("nacidos_vivos_por_mil_hab")} />
        <TarjetaIndicador
          titulo="Sin distrito conocido"
          indicador={buscaNac("nacidos_vivos_sin_ubicacion_pct", "MSP")}
        />
      </div>

      <div className="rejilla-dos">
        <div className="panel">
          <h2>
            {defNac.etiqueta} por distrito, {anioNac}
          </h2>
          <MapaDistritos
            valores={nacMapa.valores}
            unidad={nacMapa.unidad}
            seleccionado={distrito}
            onSeleccionar={setDistrito}
          />
        </div>
        <RankingDistritos
          titulo={`Los 10 distritos con más ${defNac.etiqueta.toLowerCase()}`}
          ranking={nacMapa.ranking}
          unidad={nacMapa.unidad}
          seleccionado={distrito}
          onSeleccionar={setDistrito}
        />
      </div>

      <aside className="limitacion">
        <strong>Antes de comparar años:</strong> en 2024 y 2025 una parte de los nacimientos viene sin distrito (la
        tarjeta «Sin distrito conocido» da el porcentaje del año elegido), así que las cifras por distrito de esos años
        quedan por debajo de lo real y no se pueden comparar con 2023. La fuente también separa los partos vaginales y
        por cesárea, pero ese dato es Sensible en el Diccionario y el sitio publica solo el total.
      </aside>

      <aside className="limitacion">
        <strong>Lo que esta sección no muestra:</strong> el índice de vulnerabilidad del censo (F41) es Sensible y no se
        publica. Los domicilios de una favela que cruza el límite entre distritos se reparten según el área.
      </aside>
    </section>
  );
}
