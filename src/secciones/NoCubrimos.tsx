const VACIOS = [
  {
    tema: "Turismo",
    detalle:
      "No hay hoteles ni atractivos turísticos en el lago. Los museos (F38) se descartaron y CADASTUR no está en el catálogo.",
  },
  { tema: "Seguridad", detalle: "Los datos de la SSP-SP no están en el lago. Candidata para una segunda etapa." },
  { tema: "Solicitudes ciudadanas (156)", detalle: "SP156 no está en el lago. Candidata para una segunda etapa." },
  { tema: "Valor del m²", detalle: "ITBI y la Planta Genérica de Valores no están en el lago." },
  {
    tema: "Altura real de edificios",
    detalle: "El LiDAR de la Prefeitura está fuera del lago. El mapa 3D usa alturas de OpenStreetMap.",
  },
  {
    tema: "Empleo por sector económico",
    detalle: "Las tablas de empleo solo se abren por sexo y por raza o color, no por sector.",
  },
  {
    tema: "Vegetación entre años",
    detalle:
      "La cobertura vegetal 2010, 2015 y 2020 se midió con métodos distintos, así que no se calcula la pérdida o ganancia.",
  },
];

export default function NoCubrimos() {
  return (
    <section className="seccion">
      <header className="seccion-cabecera">
        <h1>Lo que no cubrimos</h1>
        <p className="entrada">
          Esta app solo responde lo que su lago de datos sostiene. Esto es lo que queda por fuera de la versión 1.
        </p>
      </header>
      <dl className="lista-vacios">
        {VACIOS.map((v) => (
          <div key={v.tema}>
            <dt>{v.tema}</dt>
            <dd>{v.detalle}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
