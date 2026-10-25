# São Paulo · Gemelo digital

Sitio estático que responde dos preguntas con datos abiertos oficiales:

- **P1.** ¿Qué tan cubierta está la ciudad por transporte público, y dónde se concentran los equipamientos?
- **P2.** ¿Cómo se distribuye el empleo formal entre los distritos?

Todo se procesa antes, en Python. Vercel solo sirve archivos.

- [docs/COMO_FUNCIONA.md](docs/COMO_FUNCIONA.md): cómo va el dato del Excel al navegador, las secciones y el mapa 3D.
- [docs/FUENTES.md](docs/FUENTES.md): qué fuente del Diccionario se usa, para qué y cuáles quedan por fuera.

## Estructura

```
ingesta/              scripts de Python (se corren en local o en Docker)
  todo.py             corre todos los pasos en orden
  config.py           rutas, sistemas de referencia, campos sensibles, umbrales
  comun.py            reglas de limpieza compartidas (sección 5 del plan) y descarga WFS
  exportar_excel.py   Excel → data/fuentes.csv y data/diccionario.csv
  pull_territorio.py  distritos y subprefeituras desde el WFS de GeoSampa
  pull_empleo.py      F11-F17 (empleo, por sexo y por raza o color)
  pull_poblacion.py   F41 y F28 (pendiente: F01, F08)
  pull_movilidad.py   F29, F30, F31, F35, F36 (GeoSampa) y F05 (pasajeros SPTrans)
  pull_equipamientos.py  F21-F24 (ferias, shoppings), F33, F34, F39, F40 (GeoSampa) y F32 (favelas)
  pull_ambiente.py    F25-F27 (cobertura vegetal)
  calculos_p1.py      cobertura de transporte por distrito (P1)
  calculos_equipamientos.py  equipamientos y favelas por distrito
  build_web.py        lago → public/data/, con el filtro de privacidad
  verificar.py        pruebas; sale con código 1 si algo falla
data/
  Diccionario_de_datos_TallerDatos.xlsx   catálogo (fuente de verdad)
  raw/                crudos con fecha en el nombre (no se suben a git)
  lago/               CSV y GeoJSON limpios (GeoJSON en EPSG:31983); densidad_sectores, favelas y
                      empleo_raza no se suben (traen campos Sensibles), ni buses (>50 MB): se regeneran
                      con `npm run datos`
  derivados/          tablas calculadas, para revisar (no son campos del lago)
public/data/          salida para la web (sí se sube: es lo que sirve Vercel)
docs/                 cómo funciona el sitio y qué fuentes usa
src/                  Vite + React + TypeScript
```

## Correr con Docker (recomendado para el equipo)

No hace falta instalar Python, GDAL ni Node: solo Docker.

```bash
docker compose build                     # una vez, o cuando cambien requirements.txt o package.json
docker compose run --rm datos            # pipeline completo: descarga, lago, public/data, verificación
docker compose run --rm datos python ingesta/todo.py --sin-pasajeros   # sin los ~670 archivos de F05
docker compose run --rm datos python ingesta/todo.py --solo-web        # solo build_web + verificar
docker compose up web                    # sitio en http://localhost:5173
docker compose run --rm build            # compila a ./dist (lo mismo que hace Vercel)
```

En Linux, exporta `UID` y `GID` (o ponlos en un `.env`) para que los archivos queden a tu nombre.
Docker es para trabajar y reproducir; Vercel no lo usa: despliega el front con `public/data/` ya construido.

## Correr sin Docker

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
npm install

npm run datos       # pipeline completo (ingesta/todo.py)
npm run datos:web   # solo build_web + verificar
npm run dev         # http://localhost:5173
npm run build       # lo mismo que corre Vercel
npm run lint        # Biome (TS, CSS, JSON) y Ruff (Python): formato y lint
npm run formato     # aplica el formato y los arreglos automáticos
```

Para un solo paso: `cd ingesta && ../.venv/bin/python pull_empleo.py`.

La primera descarga de F05 tarda (un archivo por día, y el servidor de la Prefeitura responde 429 si se le
pide rápido); después se reutilizan los crudos de `data/raw/f05/`.

## Diseño

El sistema visual toma la señalización del Metrô de São Paulo (detalle en el encabezado de
`src/estilos.css`): fondo «concreto», recuadros planos sin bordes, cabecera como banda oscura de
señalización, tipografía Archivo (ancha en títulos, condensada en rótulos) y color solo con significado:
azul de la línea 1 para P1 y amarillo de la línea 4 para P2. Los filtros de cada sección viven en la URL
(`#transporte?metrica=paradas_por_km2&distrito=96`), así que cualquier vista se puede compartir.

## Fotos

Las fotos van a `public/fotos/` solo en WebP, en dos anchos (1.600 y 800 px), sin metadatos EXIF. El original
no se sube. Para agregar una:

```bash
.venv/bin/python herramientas/fotos_webp.py ../fotos-saopaulo/portada.jpg portada
```

La foto de portada es de Raphael Nogueira en Unsplash (licencia de Unsplash: uso libre; el crédito va en la
portada y en el pie).

## Calidad del código

- **Front:** [Biome](https://biomejs.dev) (`biome.json`), 2 espacios y 120 columnas, imports ordenados.
- **Ingesta:** [Ruff](https://docs.astral.sh/ruff/) (`ruff.toml`), 4 espacios y 120 columnas.
- Antes de un commit: `npm run formato && npm run lint && npm run verificar`.

## Mapas

`src/componentes/mapaBase.ts` arma el mapa base de OpenFreeMap solo para São Paulo: la fuente vectorial
declara `bounds` (MapLibre no pide teselas fuera de la ciudad), se quita el relieve mundial de Natural Earth
y una máscara (`territorio/municipio.geojson`, generada en `build_web.py`) tapa lo que queda fuera del
municipio. La cámara no puede salir de `LIMITES_NAVEGACION`. En modo oscuro se usa el estilo `dark` con los
edificios 3D agregados con la misma regla que Liberty.

El tema (claro u oscuro) sigue al sistema hasta que el usuario lo cambia con el botón de la cabecera; la
elección se guarda en `localStorage`. `index.html` lo aplica antes del primer pintado.

## Agregar una fuente

1. Documentar sus campos en la hoja Diccionario del Excel y correr `exportar_excel.py`.
2. Escribir o ampliar el `pull_*.py` del tema. Usar las funciones de `comun.py`, no reglas propias.
   Las columnas del archivo en `data/lago/` deben ser exactamente los campos del Diccionario.
3. Registrar el archivo en `ARCHIVOS_LAGO` de `verificar.py` y agregar sus pruebas.
4. Publicar sus indicadores en `build_web.py` con `indicador()` y `publicar_por_partes()`.
5. Si tiene campos «Sensible», agregarlos a `CAMPOS_SENSIBLES` en `config.py` (verificar.py falla si no coinciden con el Diccionario).
6. Cambiar su estado en el Excel a «Integrada al lago».

## Contrato de datos

Cada indicador en `public/data/indicadores/` trae:

| Campo | Qué es |
|---|---|
| `id` | `<indicador>_<nivel>_<código>_<vigencia>` |
| `campo_lago` | nombre exacto en la columna «Nombre del campo en el lago» del Diccionario |
| `valor`, `unidad` | la cifra |
| `nivel`, `codigo_territorio`, `nombre_territorio` | municipio, subprefeitura o distrito |
| `fuente_id`, `vigencia` | de dónde y de cuándo |
| `tipo` | `observado`, `estimado`, `proxy` o `declarado` |
| `advertencia` | obligatoria cuando el Diccionario la sugiere |
| `calculo` | solo en indicadores derivados (participación, densidad, cobertura) |
| `fuentes_adicionales` | otras fuentes que entran en el cálculo (la cobertura usa F41 + F30 + F36) |
| `transformacion` | solo en campos Sensibles que salen transformados (raza o color: `porcentaje`) |

`codigo_territorio`, `nombre_territorio`, `calculo` y `fuentes_adicionales` amplían el contrato de la
sección 6 del plan: sin ellos no se sabe a qué distrito pertenece la cifra ni de dónde sale un cálculo.
`nivel` puede ser también `linea` (pasajeros de F05, que no tiene geografía).

Empleo se publica partido: `anio_<AAAA>.json` (todos los territorios de un año, para el mapa),
`serie_<nivel>_<código>.json` (todos los años de un territorio) e `indice.json`. Transporte es una foto
actual: `indicadores/transporte/distritos.json` y `pasajeros.json`, más las capas del mapa en `transporte/`
(la red de bus y las paradas, partidas en celdas con un `indice.json`). Equipamientos, Gente y Ambiente
publican `indicadores/<seccion>/*.json` y sus capas en `equipamientos/` y `gente/`.

## P1: cómo se calcula la cobertura

`calculos_p1.py`, todo en EPSG:31983. Un sector censal (F41) está cubierto si su punto interior queda a
`RADIO_COBERTURA_M` (500 m, en `config.py`) o menos, en línea recta, de una parada de bus (F30) o estación de
metro (F36). La cobertura de área usa el mismo radio sobre el polígono del distrito. La red de bus es la unión
de los recorridos (F29), para no contar dos veces una calle con varias líneas. La copia de revisión queda en
`data/derivados/cobertura_transporte_distrito.csv`. Las estaciones de tren CPTM no entran: la capa existe en
GeoSampa (`estacao_trem`) pero no está en el catálogo.

## Privacidad

Los campos clasificados como «Sensible» están en `config.CAMPOS_SENSIBLES`, por fuente. Todo lo que
llega a `public/data/` pasa por `publicar()` en `build_web.py`, que los quita. `verificar.py`
comprueba que ninguno aparece. Decisión por defecto, pendiente de confirmar por el equipo:

- `tipo_parto` (F18-F20): no se publica; solo el total de nacidos vivos.
- `raza_color`, `empleos` (F16-F17): solo como porcentaje, suprimiendo celdas bajo `UMBRAL_SUPRESION`.
- `ubicacion_texto`, `propiedad_terreno` (F32): no se publican. `nombre` sí, por decisión del equipo
  (`PUBLICACION_AUTORIZADA` en `config.py`).
- `indice_vulnerabilidad` (F41): no se publica hasta conocer su escala y definición.

## Atribución

Prefeitura de São Paulo (GeoSampa, Infocidade), IBGE, SPTrans, Wikimedia, OpenFreeMap y
colaboradores de OpenStreetMap.
