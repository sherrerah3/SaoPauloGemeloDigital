import { formatear, type Indicador } from "../datos";
import { useFuentes } from "./contexto";

const ETIQUETA_TIPO: Record<Indicador["tipo"], string> = {
  observado: "Observado",
  estimado: "Estimado",
  proxy: "Proxy",
  declarado: "Declarado",
};

interface Props {
  titulo: string;
  indicador?: Indicador;
  destacado?: boolean;
}

/** La tarjeta siempre muestra: cifra, unidad, fuente (ID y entidad), vigencia, tipo y advertencia. */
export default function TarjetaIndicador({ titulo, indicador, destacado }: Props) {
  const fuentes = useFuentes();
  if (!indicador) {
    return (
      <article className="tarjeta cargando" aria-busy>
        <h3>{titulo}</h3>
        <p className="cifra">…</p>
      </article>
    );
  }
  const fuente = fuentes[indicador.fuente_id];
  return (
    <article className={destacado ? "tarjeta destacada" : "tarjeta"}>
      <h3>{titulo}</h3>
      <p className="cifra">
        {formatear(indicador.valor, indicador.unidad)}
        {!indicador.unidad.startsWith("%") && <span className="unidad"> {indicador.unidad.toLowerCase()}</span>}
      </p>
      <p className="territorio">
        {indicador.nombre_territorio} · {indicador.vigencia}
      </p>
      <dl className="metadatos">
        <div>
          <dt>Fuente</dt>
          <dd>
            {indicador.fuente_id}
            {fuente ? ` · ${fuente.entidad}` : ""}
            {indicador.fuentes_adicionales?.length ? ` + ${indicador.fuentes_adicionales.join(", ")}` : ""}
          </dd>
        </div>
        <div>
          <dt>Vigencia</dt>
          <dd>{indicador.vigencia}</dd>
        </div>
        <div>
          <dt>Tipo</dt>
          <dd>
            <span className={`etiqueta tipo-${indicador.tipo}`}>{ETIQUETA_TIPO[indicador.tipo]}</span>
          </dd>
        </div>
      </dl>
      {indicador.calculo && <p className="calculo">Cálculo: {indicador.calculo}</p>}
      {indicador.advertencia && (
        <p className="advertencia" role="note">
          <span aria-hidden>⚠</span> {indicador.advertencia}
        </p>
      )}
    </article>
  );
}
