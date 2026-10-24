import { lazy, Suspense, useEffect, useState } from "react";
import { cargar, type Fuente } from "./datos";
import { SECCIONES, useRuta } from "./rutas";
import Panorama from "./secciones/Panorama";
import Fuentes from "./secciones/Fuentes";
import NoCubrimos from "./secciones/NoCubrimos";
import Pendiente from "./secciones/Pendiente";
import { FuentesContexto } from "./componentes/contexto";

// MapLibre y Recharts pesan: solo se bajan al abrir una sección que los usa.
const Empleo = lazy(() => import("./secciones/Empleo"));
const Mapa3D = lazy(() => import("./secciones/Mapa3D"));
const Transporte = lazy(() => import("./secciones/Transporte"));

export default function App() {
  const ruta = useRuta();
  const [fuentes, setFuentes] = useState<Record<string, Fuente>>({});
  const [menuAbierto, setMenuAbierto] = useState(false);

  useEffect(() => {
    cargar<Fuente[]>("catalogo/fuentes.json").then((lista) =>
      setFuentes(Object.fromEntries(lista.map((f) => [f.fuente_id, f]))),
    );
  }, []);
  useEffect(() => setMenuAbierto(false), [ruta]);

  const seccion = SECCIONES.find((s) => s.id === ruta) ?? SECCIONES[0];

  return (
    <FuentesContexto.Provider value={fuentes}>
      <header className="cabecera">
        <a href="#panorama" className="marca">
          <span className="marca-punto" aria-hidden />
          São Paulo <span className="marca-sub">gemelo digital</span>
        </a>
        <button
          className="boton-menu"
          aria-expanded={menuAbierto}
          aria-controls="navegacion"
          onClick={() => setMenuAbierto((v) => !v)}
        >
          Secciones
        </button>
        <nav id="navegacion" className={menuAbierto ? "nav abierta" : "nav"}>
          {SECCIONES.map((s) => (
            <a key={s.id} href={`#${s.id}`} className={s.id === seccion.id ? "activa" : ""}>
              {s.titulo}
              {!s.lista && <span className="nav-pendiente" title="En construcción">·</span>}
            </a>
          ))}
        </nav>
      </header>

      <main className="contenido">
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
        Datos: Prefeitura de São Paulo (GeoSampa, Infocidade), IBGE, SPTrans, Wikimedia. Mapa base:
        OpenFreeMap, © colaboradores de OpenStreetMap. Cada cifra muestra su fuente y vigencia.
      </footer>
    </FuentesContexto.Provider>
  );
}
