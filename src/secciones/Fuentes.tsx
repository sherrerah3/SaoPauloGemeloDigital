import { useEffect, useMemo, useState } from "react";
import { cargar, type CampoDiccionario, type Fuente } from "../datos";
import { useFuentes } from "../componentes/contexto";

export default function Fuentes() {
  const fuentes = useFuentes();
  const [diccionario, setDiccionario] = useState<CampoDiccionario[]>([]);
  const [abierta, setAbierta] = useState<string | null>(null);
  const [filtro, setFiltro] = useState("");

  useEffect(() => {
    cargar<CampoDiccionario[]>("catalogo/diccionario.json").then(setDiccionario);
  }, []);

  const lista = useMemo(() => {
    const t = filtro.trim().toLowerCase();
    return Object.values(fuentes).filter(
      (f) => !t || `${f.fuente_id} ${f.nombre} ${f.entidad} ${f.estado}`.toLowerCase().includes(t),
    );
  }, [fuentes, filtro]);

  const conteo = (estado: string) => Object.values(fuentes).filter((f) => f.estado === estado).length;

  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <p className="antetitulo">Fuentes y método</p>
        <h1>De dónde sale cada cifra</h1>
        <p className="entrada">
          Generado desde el Excel del lago (hojas Fuentes y Diccionario). Los campos clasificados como
          «Sensible» no se publican en la app, o se publican solo como porcentaje.
        </p>
      </header>

      <div className="resumen-estados">
        <span>{Object.keys(fuentes).length} fuentes</span>
        <span>{conteo("Integrada al lago")} integradas</span>
        <span>{conteo("Candidata")} candidatas</span>
        <span>{conteo("Descartada")} descartadas</span>
      </div>

      <div className="filtros">
        <label>
          Buscar
          <input type="search" value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="ID, nombre o entidad" />
        </label>
      </div>

      <div className="tabla-scroll">
        <table className="tabla-fuentes">
          <thead>
            <tr>
              <th>ID</th>
              <th>Conjunto de datos</th>
              <th>Entidad</th>
              <th>Periodo</th>
              <th>Licencia</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((f) => (
              <FilaFuente
                key={f.fuente_id}
                fuente={f}
                campos={diccionario.filter((c) => c.fuente_id === f.fuente_id)}
                abierta={abierta === f.fuente_id}
                alternar={() => setAbierta((a) => (a === f.fuente_id ? null : f.fuente_id))}
              />
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="subtitulo">Método</h2>
      <ul className="metodo">
        <li>Todo se procesa antes, en Python; el sitio solo sirve archivos estáticos.</li>
        <li>Se mide en EPSG:31983 (SIRGAS2000 UTM 23S, metros) y se publica en EPSG:4326.</li>
        <li>
          Los nombres de distrito y subprefeitura se unen por una tabla de equivalencias construida desde las capas
          de GeoSampa; si una unidad no encuentra pareja, la verificación falla.
        </li>
        <li>Las filas «inválidos» y «no localizados» se conservan en el lago y se excluyen de mapas y rankings.</li>
        <li>Correlación no es causalidad; los pesos del atlas son una decisión analítica.</li>
      </ul>
    </section>
  );
}

function FilaFuente({ fuente, campos, abierta, alternar }: { fuente: Fuente; campos: CampoDiccionario[]; abierta: boolean; alternar: () => void }) {
  const claseEstado = fuente.estado === "Integrada al lago" ? "integrada" : fuente.estado === "Descartada" ? "descartada" : "candidata";
  return (
    <>
      <tr>
        <td>
          <button className="enlace" onClick={alternar} aria-expanded={abierta} disabled={!campos.length}>
            {fuente.fuente_id}
          </button>
        </td>
        <td>
          {fuente.url ? (
            <a href={fuente.url} target="_blank" rel="noreferrer">
              {fuente.nombre}
            </a>
          ) : (
            fuente.nombre
          )}
        </td>
        <td>{fuente.entidad}</td>
        <td>{fuente.periodo}</td>
        <td className="licencia">{fuente.licencia}</td>
        <td>
          <span className={`etiqueta estado-${claseEstado}`}>{fuente.estado}</span>
        </td>
      </tr>
      {abierta && (
        <tr className="fila-detalle">
          <td colSpan={6}>
            <table>
              <thead>
                <tr>
                  <th>Campo</th>
                  <th>Qué significa</th>
                  <th>Unidad</th>
                  <th>Clasificación</th>
                </tr>
              </thead>
              <tbody>
                {campos.map((c) => (
                  <tr key={c.campo}>
                    <td><code>{c.campo}</code></td>
                    <td>{c.significado}</td>
                    <td>{c.unidad}</td>
                    <td>{c.clasificacion === "Sensible" ? <span className="etiqueta sensible">Sensible</span> : c.clasificacion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  );
}
