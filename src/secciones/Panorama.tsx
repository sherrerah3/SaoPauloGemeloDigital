import { useEffect, useState } from "react";
import TarjetaIndicador from "../componentes/TarjetaIndicador";
import { type ArchivoIndicadores, cargar, claveIndicador, type Indicador, type IndiceSeccion } from "../datos";
import { SECCIONES } from "../rutas";

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
        <p className="antetitulo">96 distritos · 32 subprefeituras · datos abiertos oficiales</p>
        <h1>¿Dónde se mueve y dónde trabaja São Paulo?</h1>
        <p className="entrada">
          Un gemelo digital construido solo con datos abiertos oficiales. Cada cifra trae su fuente, su vigencia y si es
          observada o estimada.
        </p>
      </header>

      <div className="preguntas">
        <a href="#transporte" className="pregunta">
          <span className="pregunta-codigo">P1</span>
          <h2>¿Qué tan cubierta está la ciudad por transporte público, y dónde se concentran los equipamientos?</h2>
          <p>Buses, tren, metro, centros comerciales, mercados y equipamientos deportivos.</p>
          <span className="estado-listo">Cobertura de transporte disponible →</span>
        </a>
        <a href="#empleo" className="pregunta">
          <span className="pregunta-codigo">P2</span>
          <h2>¿Cómo se distribuye el empleo formal entre los distritos?</h2>
          <p>Por distrito, por sexo y por raza o color.</p>
          <span className="estado-listo">Empleo y establecimientos disponibles →</span>
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
