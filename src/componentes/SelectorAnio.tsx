import { useId } from "react";

interface Props {
  /** Qué año se elige: «Año del mapeo», «Año de la temperatura»… */
  etiqueta: string;
  /** Años disponibles, en cualquier orden. Pueden no ser seguidos (2010, 2015, 2020). */
  anios: string[];
  valor: string | undefined;
  onCambiar: (anio: string) => void;
}

// Con más años que esto, debajo de la barra se marcan solo los extremos (cada marca ocupa unos 36 px).
const MAX_MARCAS = 16;

/** «de 1933 a 2025» si los años son seguidos; si no, la lista: «2010, 2015 y 2020». */
function describirAnios(anios: string[]): string {
  if (anios.length === 1) return `Incluye solo ${anios[0]}`;
  const numeros = anios.map(Number);
  const seguidos = numeros.every((n, i) => i === 0 || n === numeros[i - 1] + 1);
  if (seguidos) return `Incluye ${anios.length} años: de ${anios[0]} a ${anios.at(-1)}`;
  return `Incluye ${anios.length} años: ${anios.slice(0, -1).join(", ")} y ${anios.at(-1)}`;
}

/**
 * Slider de año a todo el ancho de la sección. Recorre solo los años que existen: con años sueltos
 * (2010, 2015, 2020) cada paso salta al siguiente, no a 2011.
 */
export default function SelectorAnio({ etiqueta, anios, valor, onCambiar }: Props) {
  const id = useId();
  const ordenados = [...anios].sort((a, b) => Number(a) - Number(b));
  if (!ordenados.length) return null;

  const indice = Math.max(0, ordenados.indexOf(valor ?? ""));
  const actual = ordenados[indice];
  const ultimo = ordenados.length - 1;
  const todasLasMarcas = ordenados.length <= MAX_MARCAS;

  return (
    <div className="selector-anio">
      <p className="selector-anio-rango" id={`${id}-rango`}>
        {describirAnios(ordenados)}
      </p>
      <label className="selector-anio-etiqueta" htmlFor={id}>
        {etiqueta}: <strong>{actual}</strong>
      </label>
      <input
        id={id}
        type="range"
        min={0}
        max={ultimo}
        step={1}
        value={indice}
        disabled={ultimo === 0}
        onChange={(e) => onCambiar(ordenados[Number(e.target.value)])}
        aria-valuetext={actual}
        aria-describedby={`${id}-rango`}
      />
      <div className="selector-anio-marcas" aria-hidden>
        {ordenados.map((anio, i) => {
          const extremo = i === 0 || i === ultimo;
          if (!todasLasMarcas && !extremo) return null;
          return (
            <span
              key={anio}
              className={[
                i === 0 ? "primera" : i === ultimo ? "ultima" : "intermedia",
                anio === actual ? "activa" : "",
              ].join(" ")}
              style={{ left: ultimo ? `${(100 * i) / ultimo}%` : "50%" }}
            >
              {anio}
            </span>
          );
        })}
      </div>
    </div>
  );
}
