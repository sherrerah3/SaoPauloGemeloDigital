interface Props {
  codigo: "P1" | "P2";
}

/** El código de una pregunta como el círculo de línea del Metrô: P1 en azul (línea 1), P2 en amarillo (línea 4). */
export default function CodigoPregunta({ codigo }: Props) {
  return <span className={`codigo-pregunta codigo-${codigo.toLowerCase()}`}>{codigo}</span>;
}
