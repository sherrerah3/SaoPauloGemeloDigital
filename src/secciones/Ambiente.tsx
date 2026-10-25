import { useEffect, useMemo, useState } from "react";
import MapaDistritos from "../componentes/MapaDistritos";
import RankingDistritos from "../componentes/RankingDistritos";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import { type ArchivoIndicadores, cargar, claveIndicador, type Indicador, metricaPorTerritorio } from "../datos";
import { useParametro } from "../rutas";

const METRICAS = [
  { clave: "cobertura_vegetal_por_hab", etiqueta: "Vegetación por habitante" },
  { clave: "cobertura_vegetal_km2", etiqueta: "Superficie con vegetación" },
] as const;
type Clave = (typeof METRICAS)[number]["clave"];

// Cada año se midió distinto (satélite SPOT, RapidEye, fotos aéreas con LiDAR): no se comparan.
const ANIOS = ["2020", "2015", "2010"];

export default function Ambiente() {
  const [datos, setDatos] = useState<Indicador[]>([]);
  const [metricaUrl, setMetrica] = useParametro("metrica");
  const [anioUrl, setAnio] = useParametro("anio");
  const [subprefeitura, setSubprefeitura] = useParametro("subprefeitura");
  const def = METRICAS.find((m) => m.clave === metricaUrl) ?? METRICAS[0];
  const metrica: Clave = def.clave;
  const anio = anioUrl && ANIOS.includes(anioUrl) ? anioUrl : ANIOS[0];

  useEffect(() => {
    cargar<ArchivoIndicadores>("indicadores/ambiente/subprefeituras.json").then((a) => setDatos(a.indicadores));
  }, []);

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

      <div className="filtros">
        <label>
          Año del mapeo
          <select value={anio} onChange={(e) => setAnio(e.target.value)}>
            {ANIOS.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>
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
        sección muestra un año a la vez. La temperatura (F06) aún no está en el lago.
      </aside>
    </section>
  );
}
