# Cómo funciona el sitio

El gemelo digital es un sitio estático: todo el trabajo con datos se hace antes, en Python, y el navegador
solo baja archivos JSON y GeoJSON ya calculados. No hay servidor ni base de datos. Vercel (u otro hosting
estático) sirve la carpeta `dist/`.

```
Excel del Diccionario ──► ingesta/ (Python) ──► data/lago/ ──► build_web.py ──► public/data/ ──► sitio (React)
   catálogo de fuentes      descarga y limpia     datos limpios    filtro de         lo único que
                                                                   privacidad        ve el navegador
```

Qué fuente alimenta cada parte está en [FUENTES.md](FUENTES.md).

## 1. Del Excel al lago

1. **Catálogo.** `exportar_excel.py` lee el Excel del Diccionario y escribe `data/fuentes.csv` y
   `data/diccionario.csv`. El Excel es la fuente de verdad: nombres de campo, clasificación (Pública o
   Sensible), transformaciones y advertencias.
2. **Descarga.** Cada `pull_*.py` baja sus fuentes y guarda el crudo, con la fecha en el nombre, en
   `data/raw/`. Las capas de GeoSampa se piden por su servicio WFS; las tablas de Infocidade, por la URL del
   Excel. Si ya hay un crudo, se reutiliza. Una copia de todos los crudos está en un release de GitHub
   (`ingesta/crudos.py descargar`, ver el README), para no depender de que los servidores respondan.
3. **Limpieza.** Las reglas comunes están una sola vez en `comun.py`: números con coma decimal, «-» como
   cero cuando la fuente lo indica, años con marcas de nota («2019²»), texto mal codificado de GeoSampa,
   nombres de distrito sin tildes para unir tablas, etc.
4. **Lago.** El resultado queda en `data/lago/`: CSV para tablas y GeoJSON en EPSG:31983 (metros) para capas.
   Las columnas de cada archivo son exactamente los campos del Diccionario; `verificar.py` falla si sobra una.

| Script | Fuentes |
|---|---|
| `pull_territorio.py` | Distritos y subprefeituras (eje territorial) |
| `pull_empleo.py` | F11-F17 |
| `pull_poblacion.py` | F41, F28 |
| `pull_movilidad.py` | F05, F29-F31, F35, F36 |
| `pull_equipamientos.py` | F21-F24, F32-F34, F39, F40 |
| `pull_ambiente.py` | F25-F27 |

Todo el pipeline corre con `npm run datos` (o `docker compose run --rm datos`).

## 2. Del lago a la web

- **Cálculos.** `calculos_p1.py` mide la cobertura de transporte: un sector censal está cubierto si su punto
  interior queda a 500 m o menos, en línea recta, de una parada o estación. `calculos_equipamientos.py` cuenta
  escuelas, centros deportivos y estadios dentro de cada distrito, y reparte las favelas por área cuando cruzan
  un límite. Las copias para revisar quedan en `data/derivados/`.
- **Publicación.** `build_web.py` convierte todo en indicadores con un contrato fijo: cifra, unidad, territorio,
  fuente, vigencia, tipo (observado, estimado…), advertencia y, si es derivado, cómo se calculó. Es la única
  puerta de salida a `public/data/`.
- **Privacidad.** En esa puerta se quitan los campos Sensibles (`config.CAMPOS_SENSIBLES`): el índice de
  vulnerabilidad del censo, la calle y la propiedad del terreno de las favelas, y los conteos de empleo por raza o color,
  que solo salen como porcentaje y se suprimen bajo 10 casos. El nombre de las favelas es Sensible en el
  Diccionario, pero el equipo decidió publicarlo (ya es público en GeoSampa): la excepción, con su motivo, está
  en `config.PUBLICACION_AUTORIZADA`. Los archivos del lago que los contienen tampoco
  se suben al repositorio (`.gitignore`). Los crudos del release sí traen esos campos: son copia de
  archivos abiertos, tal como los publica cada fuente. El filtro aplica a lo que el sitio muestra.
- **Verificación.** `verificar.py` revisa que los distritos sumen el total del municipio, que nada Sensible
  llegue a `public/data/`, que ningún archivo pase de 5 MB y que todo indicador cumpla el contrato. Sale con
  error si algo falla.

## 3. El sitio

Vite, React y TypeScript (`src/`). Cada sección baja solo los archivos que necesita, y las librerías pesadas
(MapLibre para mapas, Recharts para gráficos) se cargan al abrir la primera sección que las usa.

| Sección | Qué muestra |
|---|---|
| Panorama | Las dos preguntas y las cifras clave de la ciudad. |
| Mapa 3D | La ciudad en 3D con las capas de GeoSampa. |
| Empleo (P2) | Empleo formal por distrito y año, por sexo y por raza o color. |
| Transporte y equipamientos (P1) | Cobertura de transporte, pasajeros, escuelas, deporte, ferias y shoppings. |
| Gente | Población, densidad y favelas por distrito; área construida residencial. |
| Ambiente | Vegetación por subprefeitura en 2010, 2015 y 2020. |
| Fuentes y método | El catálogo y el diccionario, generados desde el Excel. |
| Lo que no cubrimos | Lo que el lago no permite responder. |

- **Tarjetas.** Cada cifra se muestra con su fuente, entidad, vigencia, tipo y advertencia
  (`TarjetaIndicador.tsx`).
- **Mapa por distrito y ranking.** `MapaDistritos.tsx` colorea distritos (o subprefeituras) en cinco cuantiles;
  `RankingDistritos.tsx` muestra los 10 primeros o la tabla completa. Un clic en cualquiera de los dos selecciona
  el territorio.
- **URL.** La sección y sus filtros viven en el hash (`#transporte?metrica=ferias_por_10mil&distrito=96`), así
  que cualquier vista se puede compartir con un enlace.
- **Tema claro u oscuro.** Sigue al sistema hasta que se cambia con el botón de la cabecera; la elección se guarda
  en el navegador.

## El mapa 3D

- **Mapa base: OpenFreeMap.** Las calles, el agua, los parques y los edificios son teselas vectoriales de
  [OpenFreeMap](https://openfreemap.org), un servicio gratuito sin llave. Estilos: Liberty en claro y Dark en
  oscuro.
- **Datos: OpenStreetMap.** OpenFreeMap arma esas teselas con el esquema OpenMapTiles a partir de
  [OpenStreetMap](https://www.openstreetmap.org), el mapa colaborativo. De ahí salen también los edificios.
- **Altura de los edificios.** Cada edificio sube según su etiqueta `height` de OpenStreetMap o, si no la tiene,
  según `building:levels` (pisos × 3,66 m). Sin ninguno de los dos datos, queda con una altura por defecto de 5 m.
  En una muestra de teselas de octubre de 2026, los edificios en 5 m eran:

  | Zona | Edificios en 5 m |
  |---|---|
  | Avenida Paulista | 10 % |
  | Itaim Paulista | 9 % |
  | Capão Redondo | 20 % |

  Así que la mayoría sí tiene altura o número de pisos registrados. Son datos de voluntarios, no una medición
  oficial. La altura medida está en el LiDAR de la Prefeitura, que no está en el lago.
- **Solo São Paulo.** `mapaBase.ts` reescribe el estilo para que la fuente vectorial declare los límites de la
  ciudad, así que MapLibre no pide teselas de otros lugares. También quita el relieve mundial y tapa con una
  máscara lo que queda fuera del municipio. La cámara no puede alejarse más allá de un margen alrededor de la
  ciudad.
- **Capas de GeoSampa.** Las capas oficiales (metro, tren, estaciones, bus, escuelas, deporte, favelas,
  distritos) se bajan la primera vez que se encienden.
- **Red de bus y paradas por zonas.** Estas dos capas pesan unos 3 y 4 MB en total. `build_web.py` las parte en
  celdas de 0,05° (unos 5 km) y el mapa baja solo las celdas cercanas a lo que se ve, y solo al acercarse: la red
  desde zoom 12 y las paradas desde zoom 13,5. En la vista inicial (Paulista) son 9 celdas de la red, unos
  900 KB, en lugar de los 2,6 MB del archivo completo.

## 4. Desplegar

`npm run build` compila a `dist/`, con `public/data/` dentro. Vercel corre ese mismo comando; no ejecuta
Python, así que `public/data/` se sube ya construido. Docker sirve para correr el pipeline y el sitio en
cualquier máquina sin instalar Python, GDAL ni Node (ver el README).
