import { useFuentes } from "../componentes/contexto";
import type { Seccion } from "../rutas";

export default function Pendiente({ seccion }: { seccion: Seccion }) {
  const fuentes = useFuentes();
  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <p className="antetitulo">En construcción</p>
        <h1>{seccion.titulo}</h1>
        <p className="entrada">{seccion.resumen}</p>
      </header>
      {seccion.fuentes.length > 0 && (
        <div className="panel">
          <h2>Fuentes que alimentarán esta sección</h2>
          <ul className="lista-fuentes">
            {seccion.fuentes.map((id) => (
              <li key={id}>
                <span className="codigo-fuente">{id}</span> {fuentes[id]?.nombre ?? ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
