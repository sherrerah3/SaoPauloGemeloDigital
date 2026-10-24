import type { Tema } from "../tema";

interface Props {
  tema: Tema;
  onAlternar: () => void;
}

/** Muestra el icono del tema al que se cambia: la luna en claro, el sol en oscuro. */
export default function BotonTema({ tema, onAlternar }: Props) {
  const destino = tema === "claro" ? "oscuro" : "claro";
  return (
    <button
      type="button"
      className="boton-tema"
      onClick={onAlternar}
      aria-label={`Cambiar a modo ${destino}`}
      title={`Modo ${destino}`}
    >
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
        aria-hidden="true"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {tema === "claro" ? (
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        ) : (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </>
        )}
      </svg>
    </button>
  );
}
