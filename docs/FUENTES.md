# Fuentes que usa el gemelo digital

Qué fuente del Diccionario (`data/Diccionario_de_datos_TallerDatos.xlsx`) entra al sitio, para qué sirve y
dónde aparece. Los IDs son los de la hoja «1. Fuentes». El detalle de cada campo está en la hoja
«2. Diccionario» y, ya exportado, en `data/diccionario.csv` y en la sección «Fuentes y método» del sitio.

Resumen: de las 41 fuentes del catálogo, 28 están en el lago y se publican; 13 quedan por fuera (al final,
con el motivo).

## P1. Transporte y equipamientos

¿Qué tan cubierta está la ciudad por transporte público, y dónde se concentran los equipamientos?

| ID | Qué es | Publica | Para qué se usa | Archivo del lago |
|---|---|---|---|---|
| F29 | Recorridos de las líneas de bus | SPTrans, vía GeoSampa | Líneas que pasan por cada distrito y km de red (cada calle una vez). Capa «Red de bus» del mapa 3D. | `geo/buses.geojson` (no se sube: pesa 61 MB) |
| F30 | Paradas de bus | SPTrans, vía GeoSampa | Paradas por distrito y por km²; base de la cobertura a 500 m. Capa «Paradas» del mapa 3D. | `geo/paradas.geojson` |
| F31 | Líneas de tren | CPTM, vía GeoSampa | Capa «Tren CPTM» del mapa 3D. | `geo/tren.geojson` |
| F35 | Líneas de metro | SMUL, vía GeoSampa | Capa «Metro» del mapa 3D, con el color oficial de cada línea. | `geo/metro.geojson` |
| F36 | Estaciones de metro | STM, vía GeoSampa | Estaciones por distrito y cobertura por metro. | `geo/estaciones.geojson` |
| F41 | Población por sector censal, censo 2022 | IBGE, vía GeoSampa | Población cubierta a 500 m de una parada o estación; población y densidad por distrito; denominador de los indicadores «por 10 mil habitantes». | `geo/densidad_sectores.geojson` (no se sube: trae el índice de vulnerabilidad, que es Sensible) |
| F05 | Pasajeros transportados por línea | SPTrans, vía Infocidade | Serie mensual de pasajeros de los buses municipales y las 15 líneas con más pasajeros. No tiene geografía. | `sptrans_pasajeros.csv` |
| F39 | Escuelas públicas de educación infantil | SMUL, vía GeoSampa | Escuelas infantiles por distrito y por 10 mil habitantes. Capa del mapa 3D. | `geo/escuelas_infantil.geojson` |
| F40 | Escuelas públicas de enseñanza fundamental y media | SMUL, vía GeoSampa | Escuelas por distrito y por 10 mil habitantes. Capa del mapa 3D. | `geo/escuelas_basica.geojson` |
| F33 | Centros deportivos y balnearios | SEME, vía GeoSampa | Centros deportivos por distrito. Capa del mapa 3D. | `geo/centros_deportivos.geojson` |
| F34 | Estadios | SEME, vía GeoSampa | Estadios por distrito. Capa del mapa 3D. | `geo/estadios.geojson` |
| F21 | Ferias libres, mercados y sacolões, 2003-2025 | SMDHC/SESANA, vía Infocidade | Ferias por distrito y por 10 mil habitantes; mercados y sacolões por distrito (año 2025). | `ferias_mercados.csv` |
| F22 | Shoppings 2025 (censo de ABRASCE) | ABRASCE, vía Infocidade | Shoppings y área bruta locable (ABL) por distrito. | `shoppings.csv` |
| F23, F24 | Shoppings 2021 y 2017 | ABRASCE, vía Infocidade | Están en el lago, con un identificador común por shopping, para comparar años. El sitio muestra solo 2025. | `shoppings.csv` |

## P2. Empleo formal

¿Cómo se distribuye el empleo formal entre los distritos?

| ID | Qué es | Publica | Para qué se usa | Archivo del lago |
|---|---|---|---|---|
| F11 | Establecimientos formales (RAIS), 2011-2024 | MTE, vía Infocidade | Establecimientos por distrito y año. | `establecimientos_empleos.csv` |
| F12 | Empleos formales (RAIS), 2011-2024 | MTE, vía Infocidade | Empleos por distrito, participación en el municipio, empleos por km² y serie anual. | `establecimientos_empleos.csv` |
| F13, F14, F15 | Empleos formales por sexo: 2024, 2023 y 2022 | MTE, vía Infocidade | Porcentaje de empleos ocupados por mujeres, por distrito. | `empleo_sexo.csv` |
| F16, F17 | Empleos formales por raza o color: 2024 y 2023 | MTE, vía Infocidade | Porcentaje de empleos por raza o color y de personas pretas o pardas, por distrito. | `empleo_raza.csv` (no se sube: el conteo es Sensible) |

Raza o color es un campo Sensible en el Diccionario: el sitio lo muestra solo como porcentaje y suprime toda
categoría con menos de 10 empleos (`UMBRAL_SUPRESION` en `config.py`). Desde 2022 la RAIS cambió la forma de
captar los datos; cada tarjeta lo advierte.

## Gente y ambiente

| ID | Qué es | Publica | Para qué se usa | Archivo del lago |
|---|---|---|---|---|
| F32 | Favelas (polígonos) | SEHAB/HABITASAMPA, vía GeoSampa | Favelas, domicilios en favelas (número y % de los domicilios del censo) y % del área, por distrito. Capa del mapa 3D con el nombre de cada favela, sin su calle. | `geo/favelas.geojson` (no se sube: trae la calle y la propiedad del terreno, que son Sensibles) |
| F28 | Área construida residencial (catastro del IPTU), 1995-2025 | Prefeitura, vía Infocidade | Serie de la ciudad en la sección Gente. La fuente no la abre por distrito. | `area_construida_residencial.csv` |
| F25, F26, F27 | Cobertura vegetal por subprefeitura: 2020, 2015 y 2010 | SVMA, vía Infocidade | Vegetación por habitante y superficie verde por subprefeitura, un año a la vez. | `cobertura_vegetal.csv` |
| F06 | Temperatura mínima media mensual del aire, 1933-2025 | IAG/USP (estación Água Funda), vía Infocidade | Promedio anual, diferencia con la normal 1991-2020 y comparación mes a mes, en la sección Ambiente. | `temperatura_minima.csv` |

Cada año de cobertura vegetal se midió con un método distinto (satélite SPOT en 2010, RapidEye en 2015 y
fotos aéreas de 2017-2018 con LiDAR en 2020). Por eso el sitio no calcula pérdida ni ganancia entre años.

F06 sale de una sola estación meteorológica (IAG, en Água Funda), así que no representa a toda la ciudad:
por eso no hay mapa de temperatura y cada cifra lleva esa advertencia. El sitio recalcula el promedio anual y
la normal 1991-2020 a partir de los doce meses de cada año; el lago guarda solo los meses, como pide el
Diccionario.

## Base geográfica (no son fuentes del catálogo)

- **Distritos y subprefeituras** de GeoSampa (WFS): el eje territorial de todo el lago.
- **Mapa base y edificios 3D**: teselas vectoriales de [OpenFreeMap](https://openfreemap.org), hechas con
  datos de © colaboradores de [OpenStreetMap](https://www.openstreetmap.org). Más detalle en
  [COMO_FUNCIONA.md](COMO_FUNCIONA.md#el-mapa-3d).

## Fuentes del catálogo que no entran (todavía)

| ID | Qué es | Por qué no está |
|---|---|---|
| F01 | Población histórica 1872-2022 | Pendiente; la población actual ya sale del censo 2022 (F41). |
| F02 | Visitas al artículo «São Paulo» en Wikipedia | No responde ninguna de las dos preguntas. |
| F03 | Establecimientos de salud | Pendiente para la sección «Municipio». |
| F04 | Ingresos y gastos municipales | Pendiente para la sección «Municipio». |
| F07 | IDH municipal, 2000 y 2010 | Desactualizado. |
| F08 | Estimación de población del IBGE | La API (`servicodados.ibge.gov.br`) no respondía al integrarla, en octubre de 2026. |
| F09 | Olho Vivo (buses en tiempo real) | Necesita llave y un servidor; el sitio es estático. |
| F10 | Tráfico del portal de datos abiertos | Descartada en el catálogo. |
| F18-F20 | Nacimientos y tipo de parto | Pendiente; `tipo_parto` es Sensible. |
| F37 | Curvas de nivel | Muy pesada para un sitio estático. |
| F38 | Museos | Descartada por el equipo en el catálogo. |

## Fuentes nuevas propuestas

`GestionGobernanza/Diccionario_de_datos_FuentesNuevas.xlsx` (fuera del repositorio) documenta, con el mismo
formato, nueve fuentes oficiales más para una segunda etapa: atractivos turísticos y equipamientos culturales
de GeoSampa, demanda por estación del Metrô y hospedajes de CADASTUR. Ese archivo numera sus fuentes de F42 a
F50; si se integran al Excel principal, conviene revisar que esos IDs sigan libres.

## Estado en el Excel

La columna «Estado» del Excel todavía marca como «Candidata» las fuentes que ya están integradas.
`verificar.py` lo avisa al final. Hay que cambiarlo a «Integrada al lago» en el Excel original (este
repositorio no lo modifica) y volver a correr `exportar_excel.py`.
