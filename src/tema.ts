import { createContext, useCallback, useContext, useEffect, useState } from "react";

// Claro u oscuro. index.html lo aplica antes de pintar (atributo data-tema en <html>) para que la
// página no parpadee; este módulo lo mantiene sincronizado y guarda la elección del usuario.

export type Tema = "claro" | "oscuro";

const CLAVE = "tema";
const CONSULTA_OSCURO = "(prefers-color-scheme: dark)";

function temaGuardado(): Tema | null {
  try {
    const valor = localStorage.getItem(CLAVE);
    return valor === "claro" || valor === "oscuro" ? valor : null;
  } catch {
    return null; // navegación privada o almacenamiento bloqueado
  }
}

function temaDelSistema(): Tema {
  return window.matchMedia(CONSULTA_OSCURO).matches ? "oscuro" : "claro";
}

/** El tema activo y la función para alternarlo. Sin elección guardada, sigue al sistema. */
export function useTemaRaiz(): [Tema, () => void] {
  const [tema, setTema] = useState<Tema>(() => temaGuardado() ?? temaDelSistema());

  useEffect(() => {
    document.documentElement.dataset.tema = tema;
  }, [tema]);

  useEffect(() => {
    const consulta = window.matchMedia(CONSULTA_OSCURO);
    const alCambiar = () => {
      if (!temaGuardado()) setTema(temaDelSistema());
    };
    consulta.addEventListener("change", alCambiar);
    return () => consulta.removeEventListener("change", alCambiar);
  }, []);

  const alternar = useCallback(() => {
    setTema((actual) => {
      const nuevo = actual === "claro" ? "oscuro" : "claro";
      try {
        localStorage.setItem(CLAVE, nuevo);
      } catch {
        // sin almacenamiento la elección dura hasta recargar
      }
      return nuevo;
    });
  }, []);

  return [tema, alternar];
}

export const TemaContexto = createContext<Tema>("claro");

export const useTema = () => useContext(TemaContexto);
