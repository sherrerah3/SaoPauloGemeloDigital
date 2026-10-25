import { useEffect, useState } from "react";
import CodigoPregunta from "../componentes/CodigoPregunta";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import { type ArchivoIndicadores, cargar, claveIndicador, type Indicador, type IndiceSeccion } from "../datos";
import { SECCIONES } from "../rutas";

// Versiones WebP de herramientas/fotos_webp.py; el navegador elige el ancho según la pantalla.
const FOTOS = `${import.meta.env.BASE_URL}fotos/`;

export default function Panorama() {
  const [municipio, setMunicipio] = useState<Indicador[]>([]);

  useEffect(() => {
    const empleo = cargar<IndiceSeccion>("indicadores/empleo/indice.json").then((i) =>
      cargar<ArchivoIndicadores>(`indicadores/empleo/anio_${i.anios[i.anios.length - 1]}.json`),
    );
    const transporte = cargar<ArchivoIndicadores>("indicadores/transporte/distritos.json");
    Promise.all([empleo, transporte]).then((archivos) =>
      setMunicipio(archivos.flatMap((a) => a.indicadores.filter((i) => i.nivel === "municipio"))),
    );
  }, []);

  const busca = (clave: string) => municipio.find((i) => claveIndicador(i) === clave);
  const listas = SECCIONES.filter((s) => s.lista).length;

  return (
    <section className="seccion">
      <header className="portada">
        <img
          className="portada-foto"
          src={`${FOTOS}portada-1600.webp`}
          srcSet={`${FOTOS}portada-800.webp 800w, ${FOTOS}portada-1600.webp 1600w`}
          sizes="(max-width: 1232px) 100vw, 1200px"
          width={1600}
          height={1067}
          alt="Ponte Estaiada sobre el río Pinheiros, con edificios de oficinas al fondo"
          fetchPriority="high"
        />
        <div className="portada-texto">
          <h1>¿Dónde se mueve y dónde trabaja São Paulo?</h1>
          <p className="entrada">
            Los 96 distritos y 32 subprefeituras de la ciudad, contados solo con datos abiertos oficiales. Cada cifra
            dice de qué fuente sale, de cuándo es y si es observada o estimada.
          </p>
        </div>
        <p className="portada-credito">
          Foto: <a href="https://unsplash.com/photos/0phxYpfFHpg">Raphael Nogueira</a> en Unsplash
        </p>
      </header>

      <div className="preguntas">
        <a href="#transporte" className="pregunta">
          <CodigoPregunta codigo="P1" />
          <div className="pregunta-cuerpo">
            <h2>¿Qué tan cubierta está la ciudad por transporte público, y dónde se concentran los equipamientos?</h2>
            <p>Buses, tren, metro, centros comerciales, mercados y equipamientos deportivos.</p>
            <span className="pregunta-accion">Ver cobertura de transporte</span>
          </div>
        </a>
        <a href="#empleo" className="pregunta">
          <CodigoPregunta codigo="P2" />
          <div className="pregunta-cuerpo">
            <h2>¿Cómo se distribuye el empleo formal entre los distritos?</h2>
            <p>Por distrito, por sexo y por raza o color.</p>
            <span className="pregunta-accion">Ver empleo por distrito</span>
          </div>
        </a>
      </div>

      <h2 className="subtitulo">Cifras clave</h2>
      <div className="rejilla-tarjetas">
        <TarjetaIndicador
          titulo="Habitantes a 500 m o menos de una parada o estación"
          indicador={busca("cobertura_poblacion")}
          destacado
        />
        <TarjetaIndicador titulo="Empleos formales en la ciudad" indicador={busca("empleos_formales")} destacado />
        <TarjetaIndicador titulo="Población (censo 2022)" indicador={busca("poblacion")} />
      </div>
      <p className="nota">
        Pendientes para esta portada: población histórica (F01, F08) y finanzas municipales (F04). Secciones con datos:{" "}
        {listas} de {SECCIONES.length}.
      </p>
    </section>
  );
}
