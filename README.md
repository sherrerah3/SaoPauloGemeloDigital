# São Paulo · sistema de información

Grupo: Samuel Herrera Hoyos, Samuel Henao Castrillón, Juan José Gómez Ramírez y Juan Carlos Fernández Vanoy
· Despliegue: sitio estático, publicable en Vercel con `npm run build` · Revisado: 2026-11-03

Un gemelo digital de São Paulo hecho solo con datos abiertos oficiales. Todo se procesa antes, en Python; el
sitio es estático y cada cifra dice de dónde sale, de cuándo es y cuándo se probó la fuente.

Más detalle: [cómo funciona](docs/COMO_FUNCIONA.md) · [qué fuente se usa para qué](docs/FUENTES.md) ·
[guía técnica](docs/DESARROLLO.md) · catálogo y diccionario en
[`data/Diccionario_de_datos_TallerDatos.xlsx`](data/Diccionario_de_datos_TallerDatos.xlsx).

## Para quién y qué pregunta

- **Usuario:** secretarías municipales, inversionistas del sector inmobiliario, organizaciones comunitarias,
  investigadores y visitantes que no conocen la ciudad.
- **Preguntas:**
  1. **P1.** ¿Qué tan cubierta está la ciudad por transporte público, y dónde se concentran los equipamientos?
     Respondida con la cobertura a 500 m de paradas y estaciones, escuelas, deporte, ferias y shoppings.
     _Fuera de alcance:_ atractivos turísticos, hoteles y equipamientos culturales (fuentes F42-F50, propuestas
     para una segunda etapa y no integradas).
  2. **P2.** ¿Dónde conviene montar un negocio en São Paulo? Para un inversionista: dónde hay clientes, cuánta
     competencia hay y si se llega en transporte público. Dos perfiles (negocio de barrio y negocio para
     trabajadores) con un puntaje proxy por distrito, más el empleo formal y su evolución. Reemplaza a la P2 de
     la primera entrega («¿Cómo se distribuye el empleo formal entre los distritos?»), con acuerdo del profesor:
     esa distribución sigue en la sección, pero ahora al servicio de una decisión. _Fuera de alcance:_ arriendos
     y precios del suelo, ingreso por distrito y sector económico (no están en el lago).
  3. **P3.** ¿Los distritos con más favelas reciben menos? Compara transporte, empleo, deporte y escuelas
     públicas entre el 25 % de los distritos con más domicilios en favelas y el 25 % con menos, y muestra quién
     ocupa el empleo formal por raza o color y sexo. _Fuera de alcance:_ salud por distrito (la red de salud del
     lago viene solo para toda la ciudad).
  4. Preguntas de contexto: ¿dónde vive la gente? (Gente), ¿con qué red de salud y presupuesto cuenta la ciudad?
     (Municipio) y ¿cuánto verde tiene cada zona? (Ambiente).
- **Escala y comparación:** 96 distritos y 32 subprefeituras, siempre contra el total del municipio. Series
  anuales donde la fuente las tiene (empleo 2011-2024, finanzas 2016-2025, población desde 1872).
- **Lo que decidimos no mostrar, y por qué:**
  - El índice de vulnerabilidad del censo por sector (F41): señala manzanas concretas como «vulnerables».
  - La calle y la propiedad del terreno de cada favela (F32): ubican comunidades puntuales. El nombre sí se
    muestra, porque ya es público en GeoSampa.
  - El tipo de parto (F18-F20): en distritos con pocos nacimientos se acerca a identificar a una madre. Se
    publica solo el total.
  - Los conteos de empleo por raza o color (F16-F17): salen solo como porcentaje, y una categoría con menos de
    10 empleos no se muestra.
  - El área construida residencial (F28): está en el lago, pero es una sola cifra para la ciudad y no ayuda a
    ninguna pregunta.
  - El crecimiento del empleo por distrito como señal para invertir: la RAIS cuenta los empleos donde la empresa
    registra su sede, y una mudanza de sede mueve cientos de miles de empleos (Brás pasó de 73 mil a 420 mil en
    2022 y volvió a 76 mil en 2023). Mostrarlo como «distrito que crece» engañaría al inversionista.

## La réplica

- **Qué replicamos y qué cambiamos:** replicamos los seis tramos (fuentes, catálogo, ingesta,
  lago, verificación y vistas) y la regla de que cada cifra lleve fuente, vigencia y fecha de prueba. Para São
  Paulo cambiamos:
  - El eje territorial: distritos y subprefeituras de GeoSampa, unidos por una tabla de equivalencias.
  - Las capas geográficas, que se piden al servicio WFS de GeoSampa y se miden en metros (EPSG:31983).
  - Los crudos, que quedaron congelados en un release, porque GeoSampa llegó a publicar vacía la capa de
    paradas.
- **Fuentes:** 41 catalogadas.
  - **35 integradas al lago:** 32 se ven en el sitio y 3 están solo en el lago (F23, F24 y F28).
  - **1 caída:** F08, porque la API del IBGE no respondía.
  - **3 no integradas:** F02, F09 y F37.
  - **2 descartadas:** F10 y F38.

  El Excel tiene solo las 35 del lago. Las otras 6, con su motivo, están en [docs/FUENTES.md](docs/FUENTES.md)
  y en la sección «Fuentes y método» del sitio.
- **Huecos:**
  - El empleo por sector económico.
  - Los atractivos turísticos, hoteles y equipamientos culturales.
  - Las estaciones de tren CPTM: la capa existe en GeoSampa, pero no está en el catálogo.
  - Los buses en tiempo real: Olho Vivo pide un token y un servidor.

## ¿Se puede usar?

| Fuente | Licencia | Personas | Estado | Condición |
|---|---|---|---|---|
| F01, F03, F04, F06, F07, F21-F28 (Prefeitura, Infocidade) | no declara | No | Integrada al lago | Información pública por la Ley de Acceso a la Información (LAI); se cita la fuente |
| F11-F17 (RAIS del MTE, vía Infocidade) | no declara | Solo conteos por zona | Integrada al lago | Raza o color solo en porcentaje, con supresión bajo 10 |
| F18-F20 (nacimientos, SINASC) | no declara | Solo conteos por zona | Integrada al lago | Se publica solo el total; el tipo de parto no |
| F05 (pasajeros de SPTrans) | CC0 (según el catálogo; la fuente no la declara en el archivo) | No | Integrada al lago | Sin geografía: solo por línea y mes |
| F29-F31, F33-F36, F39, F40 (GeoSampa) | no declara | No | Integrada al lago | Capas oficiales de la Prefeitura; se cita la fuente |
| F32 (favelas, GeoSampa) | no declara | Solo conteos por zona | Integrada al lago | Sin calle ni propiedad del terreno |
| F41 (censo 2022 por sector, IBGE vía GeoSampa) | no declara | Solo conteos por zona | Integrada al lago | Sin índice de vulnerabilidad; se agrega por distrito |
| Mapa base (OpenFreeMap, datos de OpenStreetMap) | ODbL | No | Usada en las vistas | Atribución a OpenStreetMap en el mapa |

«No declara» es literal: la fuente no publica una licencia. Lo que entendemos de ella va en «Observaciones» del
Excel, no en la columna de licencia.

## Bitácora de exploración

El piso pide dos herramientas probadas por tramo con los mismos datos. La segunda fila de cada tramo es la
herramienta que el equipo evaluó con los mismos datos y no adoptó, con el motivo.

| Tramo | Herramienta | Qué pidió para empezar | Licencia | Dónde quedan los datos | ¿Se rehace con un comando? | Estado del proyecto | Qué resolvió | Qué no pudo | ¿Quedó? ¿Por qué? |
|---|---|---|---|---|---|---|---|---|---|
| Catálogo | Excel del taller | Nada: la plantilla del curso | Archivo propio | En el repositorio | Sí: `exportar_excel.py` lo pasa a CSV | Activo | Una sola fuente de verdad para fuentes y campos | Validar solo: eso lo hace `verificar.py` | Sí: es el formato de la entrega |
| Catálogo | Google Sheets | Cuenta de Google del equipo | Servicio propietario (gratis) | En la nube de Google | Parcial: hay que exportar a `.xlsx` a mano antes de `exportar_excel.py` | Evaluada | Edición simultánea del catálogo entre los cuatro | No vive en git: no hay historial ni diff por celda, y ata el dato a una cuenta externa | No: el Excel en el repositorio da versionado y es el formato que pide la entrega |
| Ingesta | Python (pandas, geopandas) | Python 3.12 y GDAL (o Docker) | BSD-3 | `data/raw/` y `data/lago/` en la máquina | Sí: `npm run datos` | Activo | WFS de GeoSampa, Excel viejos y nuevos, cruces geográficos | | Sí: la misma herramienta sirve para limpiar y para cruzar mapas |
| Ingesta | Python plano (`requests` + módulo `csv`), sin pandas | Python 3.12 | Apache-2.0 / PSF | `data/raw/` y `data/lago/` en la máquina | Sí: `npm run datos` | Evaluada | Bajar y guardar los crudos con menos dependencias | No reproyecta ni cruza geometrías: los Excel con celdas combinadas y las capas WFS obligan a escribir a mano lo que geopandas ya resuelve | No: sin geopandas había que reimplementar el cruce territorial y el manejo de CRS |
| Lago | Archivos CSV y GeoJSON | Nada | Formatos abiertos | `data/lago/`; los Sensibles no se suben | Sí: `npm run datos` | Activo | Legibles por cualquier herramienta; diferencias visibles en git | Consultas pesadas | Sí: el lago es chico (cientos de MB) |
| Lago | DuckDB (base de un archivo) | El binario de DuckDB | MIT | Un `.duckdb` en la máquina | Sí: `npm run datos` | Evaluada | Consultas SQL y cruces rápidos sobre las tablas del lago | El archivo binario no da diff por fila en git y suma una dependencia; el GeoJSON hay que exportarlo igual para el mapa | No: a esta escala el CSV basta y el versionado legible pesa más que la velocidad de consulta |
| Verificación | `verificar.py` propio | Nada | Código del equipo | No guarda datos | Sí: `npm run verificar` | Activo | Sumas contra el total, columnas contra el Diccionario, que nada Sensible llegue a la web | | Sí |
| Verificación | Pandera (esquemas declarativos) | Python 3.12 | MIT | No guarda datos | Sí: `npm run verificar` | Evaluada | Validar tipos y rangos de cada columna con un esquema corto | No expresa las reglas de negocio del proyecto (distritos que suman el total, nada Sensible en `public/data/`): habría que escribirlas igual en Python aparte | No: las pruebas propias cubren esquema y reglas en un solo lugar, sin una dependencia más |
| Vistas | React + MapLibre GL JS + Recharts, en Vercel | Node; sin llave ni tarjeta | MIT, BSD-3, MIT; Vercel con plan gratis | JSON estáticos en Vercel; solo agregados | Sí: `npm run build` | Activo | Mapa 3D, mapas por distrito, gráficos y notas por cifra | | Sí: no necesita servidor ni llave |
| Vistas | Streamlit | Python 3.12 | Apache-2.0 | Un proceso de Python sirviendo las vistas | Sí: `streamlit run` | Evaluada | Mapas y gráficos con muy poco código | Necesita un servidor de Python corriendo: rompe la regla de sitio estático sin servidor y no da el mapa 3D con las capas oficiales | No: el requisito era un sitio estático sin servidor ni llave, que Streamlit no cumple |

## Protección

- **Nivel:** abierto. Todas las fuentes son abiertas y oficiales: cualquier persona puede descargar los mismos
  archivos de la Prefeitura, el IBGE o SPTrans. Por eso no hay compuerta: una clave sería teatro. Aun así, el
  sitio muestra solo agregados por zona y deja fuera los campos que el Diccionario marca como Sensibles.
- **Qué protegemos, y de quién:** a las personas de zonas pequeñas frente a la reidentificación (madres por
  tipo de parto, trabajadores por raza o color) y a las comunidades frente al señalamiento (calle de una
  favela, manzanas «vulnerables»).
- **Cómo:**
  - `build_web.py` es la única salida a la web: quita los campos Sensibles (`CAMPOS_SENSIBLES` en `config.py`)
    y suprime las celdas bajo 10.
  - `verificar.py` falla si un campo Sensible llega a `public/data/`.
  - Los archivos del lago con esos campos no se suben al repositorio (`.gitignore`).
  - Los crudos están en un release del repositorio: son copia exacta de archivos que ya son públicos. Lo
    decidimos así para que cualquiera reconstruya el lago aunque los servidores no respondan. El filtro de
    Sensibles aplica a lo que el sitio muestra, no a la copia de archivos abiertos.
- **Pruebas:** `npm run verificar` («ningún campo Sensible llega a public/data»). El sitio no tiene compuerta,
  así que no hay prueba de ventana privada.
- **Secretos en el historial:** revisado el 2026-11-03 con una búsqueda de llaves, tokens y claves en los 42
  commits. No hay ninguno: el sitio no usa llaves (OpenFreeMap no la pide).

## Herramienta elegida para las vistas

- **Qué necesitábamos mostrar:**
  - Mapas por distrito y por subprefeitura.
  - La ciudad en 3D con las capas oficiales.
  - Series y rankings.
  - Fuente, vigencia y fecha de prueba de cada cifra, a un clic.
- **Qué teníamos que proteger:** solo agregados, sin servidor que guarde datos.
- **Por qué cumple:**
  - React con MapLibre y Recharts genera un sitio estático, sin llave ni tarjeta.
  - Los datos son JSON que ya pasaron el filtro de privacidad.
  - El mapa base de OpenFreeMap es gratis y sin registro.
  - Cada tarjeta lleva un número que remite a su nota al final de la sección.

## Nuestra posición

- **Datos: «El catálogo pasó de documentación a infraestructura».** De acuerdo, y nuestro sistema lo muestra:
  - El Excel no es un anexo. `exportar_excel.py` lo convierte en lo que leen los scripts.
  - `verificar.py` falla si una columna del lago no está en el Diccionario, o si un campo marcado Sensible
    llega a la web.
  - El estado de cada fuente en el sitio se calcula de lo que de verdad se publica.

  Cuando el catálogo decía «Candidata» para fuentes ya integradas, la verificación lo avisaba.
- **Seguridad: «La herramienta que ayuda también puede actuar».** De acuerdo.
  - **Qué hacía la IA:** el asistente que construyó buena parte del código (Claude Code) trabajaba con el
    repositorio y la terminal.
  - **Qué datos veía:** solo datos abiertos oficiales. El lago no tiene datos privados, y la IA nunca vio
    credenciales: el inicio de sesión en GitHub lo hizo el estudiante en su terminal.
  - **Qué no podía hacer sola:** commits, push y merges solo con pedido explícito. Todo cambio lo revisó y lo
    verificó un estudiante antes de subirlo. La publicación de un release la bloqueó el control de permisos del
    asistente y la tuvo que hacer una persona.
  - **Dónde podría haber instrucciones escondidas:** en el texto libre del lago, como nombres de favelas y de
    shoppings, u observaciones de las fuentes. Lo tratamos como dato: ningún script lo ejecuta ni se lo pasa a
    un asistente como instrucción.

## Bitácora de IA

La bitácora completa está en la hoja «3. Bitácora IA» del Excel. Los errores pesan tanto como los aciertos:

| Qué pasó | Resultado | Cómo nos dimos cuenta | Qué cambiamos |
|---|---|---|---|
| La IA escribió la licencia de dominio público como «CCO» en lugar de «CC0» | Incorrecto | Revisión de la fuente | Se corrigió en el catálogo |
| Dio enlaces a fuentes ya deprecadas | Incorrecto | Los enlaces no abrían | Se buscaron las URL vigentes |
| Inventó un alias «jaguare» → «jaguara» para cruzar shoppings | Inventado | Jaguaré es un distrito real de GeoSampa | Se quitó; toda equivalencia se contrasta con la capa oficial |
| Publicó JSON con NaN | Incorrecto | La página de empleo no cargaba un año | `build_web.py` falla si vuelve a pasar |
| Afirmó que las capas de bus se bajaban al abrir el mapa | Incorrecto | Leímos el código: estaban apagadas | Lo que se afirma del código se comprueba en el código |
| Encontró que GeoSampa devolvía vacía la capa de paradas | Correcto | Pedimos la capa al WFS: 0 elementos | Crudos congelados en un release |
| Vio «Sin dato» y cifras raras en capturas automáticas | Parcial | En Chrome las cifras estaban bien | Antes de corregir, se confirma en el navegador |

## Cómo correrlo

Con Docker, sin instalar nada más:

```bash
docker compose build
docker compose run --rm datos   # baja la copia de los crudos, arma el lago, publica y verifica
docker compose up web           # http://localhost:5173
```

Sin Docker: `npm run datos`, `npm run verificar` y `npm run dev` (instalación en
[docs/DESARROLLO.md](docs/DESARROLLO.md)).

Atribución: Prefeitura de São Paulo (GeoSampa, Infocidade), IBGE, SPTrans, MTE (RAIS), ABRASCE, OpenFreeMap y
colaboradores de OpenStreetMap. Fotos: Raphael Nogueira (Unsplash) y autores de Wikimedia Commons.
