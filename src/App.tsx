import { lazy, Suspense, useEffect, useState } from "react";
import BotonTema from "./componentes/BotonTema";
import { FuentesContexto } from "./componentes/contexto";
import { cargar, type Fuente } from "./datos";
import { SECCIONES, useRuta } from "./rutas";
import Fuentes from "./secciones/Fuentes";
import NoCubrimos from "./secciones/NoCubrimos";
import Panorama from "./secciones/Panorama";
import Pendiente from "./secciones/Pendiente";
import { TemaContexto, useTemaRaiz } from "./tema";

// MapLibre y Recharts pesan: solo se bajan al abrir una sección que los usa.
const Empleo = lazy(() => import("./secciones/Empleo"));
const Mapa3D = lazy(() => import("./secciones/Mapa3D"));
const Transporte = lazy(() => import("./secciones/Transporte"));

// Las rutas viven en el hash, así que el salto no puede ser un enlace a #contenido: mueve el foco.
function irAlContenido() {
  document.getElementById("contenido")?.focus();
}

export default function App() {
  const ruta = useRuta();
  const [fuentes, setFuentes] = useState<Record<string, Fuente>>({});
  // El menú (móvil) queda abierto solo en la sección donde se abrió: al navegar se cierra.
  const [menuAbiertoEn, setMenuAbiertoEn] = useState<string | null>(null);
  const menuAbierto = menuAbiertoEn === ruta;
  const [tema, alternarTema] = useTemaRaiz();

  useEffect(() => {
    cargar<Fuente[]>("catalogo/fuentes.json").then((lista) =>
      setFuentes(Object.fromEntries(lista.map((f) => [f.fuente_id, f]))),
    );
  }, []);

  const seccion = SECCIONES.find((s) => s.id === ruta) ?? SECCIONES[0];

  return (
    <TemaContexto.Provider value={tema}>
      <FuentesContexto.Provider value={fuentes}>
        <button type="button" className="saltar" onClick={irAlContenido}>
          Saltar al contenido
        </button>
        <header className="cabecera">
          <a href="#panorama" className="marca">
            <span className="marca-punto" aria-hidden />
            <span translate="no">São Paulo</span> <span className="marca-sub">gemelo digital</span>
          </a>
          <button
            type="button"
            className="boton-menu"
            aria-expanded={menuAbierto}
            aria-controls="navegacion"
            aria-label="Secciones"
            onClick={() => setMenuAbiertoEn(menuAbierto ? null : ruta)}
          >
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              aria-hidden="true"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d={menuAbierto ? "M6 6l12 12M18 6L6 18" : "M4 7h16M4 12h16M4 17h16"} />
            </svg>
          </button>
          <nav id="navegacion" className={menuAbierto ? "nav abierta" : "nav"}>
            {SECCIONES.map((s) => (
              <a key={s.id} href={`#${s.id}`} className={s.id === seccion.id ? "activa" : ""}>
                {s.titulo}
                {!s.lista && (
                  <span className="nav-pendiente" title="En construcción">
                    ·
                  </span>
                )}
              </a>
            ))}
          </nav>
          <BotonTema tema={tema} onAlternar={alternarTema} />
        </header>

        <main id="contenido" className="contenido" tabIndex={-1}>
          <Suspense fallback={<p className="nota">Cargando…</p>}>
            {seccion.id === "panorama" && <Panorama />}
            {seccion.id === "mapa" && <Mapa3D />}
            {seccion.id === "empleo" && <Empleo />}
            {seccion.id === "transporte" && <Transporte />}
            {seccion.id === "fuentes" && <Fuentes />}
            {seccion.id === "no-cubrimos" && <NoCubrimos />}
            {!seccion.lista && <Pendiente seccion={seccion} />}
          </Suspense>
        </main>

        <footer className="pie">
          Datos: Prefeitura de São Paulo (GeoSampa, Infocidade), IBGE, SPTrans, Wikimedia. Mapa base: OpenFreeMap, ©
          colaboradores de OpenStreetMap. Cada cifra muestra su fuente y vigencia.
        </footer>
      </FuentesContexto.Provider>
    </TemaContexto.Provider>
  );
}
