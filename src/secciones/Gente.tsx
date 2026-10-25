import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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

export default function Gente() {
  const [datos, setDatos] = useState<Indicador[]>([]);
  const [area, setArea] = useState<Indicador[]>([]);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [distrito, setDistrito] = useParametro("distrito");
  const def = METRICAS.find((m) => m.clave === metricaUrl) ?? METRICAS[0];
  const metrica: Clave = def.clave;

  useEffect(() => {
    const gente = cargar<ArchivoIndicadores>("indicadores/gente/distritos.json");
    const transporte = cargar<ArchivoIndicadores>("indicadores/transporte/distritos.json");
    Promise.all([gente, transporte]).then(([g, t]) =>
      setDatos([...g.indicadores, ...t.indicadores.filter((i) => DE_TRANSPORTE.has(claveIndicador(i)))]),
    );
    cargar<ArchivoIndicadores>("indicadores/gente/area_construida.json").then((a) => setArea(a.indicadores));
  }, []);

  const { valores, ranking, unidad } = useMemo(() => metricaPorTerritorio(datos, metrica), [datos, metrica]);

  const territorio = distrito ?? "MSP";
  const busca = (clave: string) => datos.find((i) => i.codigo_territorio === territorio && claveIndicador(i) === clave);
  const nombreTerritorio = busca("poblacion")?.nombre_territorio ?? "Município de São Paulo";
  const serieArea = area.map((i) => ({ anio: i.vigencia, valor: i.valor }));

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <h1>¿Dónde vive la gente?</h1>
        <p className="entrada">
          Población y densidad del censo 2022 y las favelas que delimita la Secretaría de Vivienda (HABITASAMPA), por
          distrito. En el mapa 3D cada favela muestra su nombre, pero no su calle.
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

      <aside className="limitacion">
        <strong>Lo que esta sección no muestra todavía:</strong> población histórica (F01), IDH municipal (F07) y
        nacimientos (F18-F20). El índice de vulnerabilidad del censo (F41) es Sensible y no se publica. Los domicilios
        de una favela que cruza el límite entre distritos se reparten según el área.
      </aside>
    </section>
  );
}
