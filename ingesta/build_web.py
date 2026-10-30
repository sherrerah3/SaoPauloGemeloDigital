"""Lee el lago y escribe public/data/ para la web (secciones 6 y 7 del plan).

Todo lo que llega a public/ pasa por publicar(), que aplica el filtro de privacidad.
No se escribe en public/ de ninguna otra forma.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import shutil

import geopandas as gpd
import pandas as pd
import shapely

import calculos_equipamientos
import calculos_p1
from comun import cargar_equivalencias, unir_distritos, unir_subprefeituras
from config import (
    CAMPOS_SENSIBLES,
    CRS_TRABAJO,
    CRS_WEB,
    DICCIONARIO_CSV,
    FUENTES_CSV,
    LAGO,
    LAGO_GEO,
    PUBLIC_DATA,
    PUBLICACION_AUTORIZADA,
    PUBLICACION_TRANSFORMADA,
    RADIO_COBERTURA_M,
    RAW,
    UMBRAL_SUPRESION,
)

TIPOS = {"observado", "estimado", "proxy", "declarado"}

# Advertencias que el Diccionario sugiere; son obligatorias en la tarjeta.
ADVERTENCIAS = {
    "F06": "Medida en una sola estación (IAG Água Funda); no representa toda la ciudad.",
    "F08": "Es una estimación del IBGE para 2021, no un conteo.",
    "F11": "Son establecimientos con registro formal (RAIS), no empresas ni empleos. "
    "La serie RAIS tiene un quiebre desde 2022 por cambios en la captación.",
    "F12": "Mide dónde está el empleo, no dónde vive quien lo ocupa. "
    "La serie RAIS tiene un quiebre desde 2022 por cambios en la captación.",
    "F05": "Solo buses municipales de SPTrans (no metro ni tren). Se suman los reportes diarios; "
    "un mes al que le falta algún día se completa con el consolidado mensual de SPTrans.",
    "F13": "La serie RAIS tiene un quiebre desde 2022 por cambios en la captación.",
    "F14": "La serie RAIS tiene un quiebre desde 2022 por cambios en la captación.",
    "F15": "La serie RAIS tiene un quiebre desde 2022 por cambios en la captación.",
    "F16": "Porcentaje sobre todos los empleos, incluidos los que no tienen raza o color registrada.",
    "F17": "Porcentaje sobre todos los empleos, incluidos los que no tienen raza o color registrada.",
    "F25": "El método de medición cambia entre años; no comparar 2010, 2015 y 2020.",
    "F26": "El método de medición cambia entre años; no comparar 2010, 2015 y 2020.",
    "F27": "El método de medición cambia entre años; no comparar 2010, 2015 y 2020.",
    "F01": "De 1872 a 1950 son personas presentes, de 1960 a 1980 personas recenseadas y desde 1991 residentes: "
    "la serie no mide siempre lo mismo.",
    "F07": "Es el IDHM de 2000 y 2010 (Atlas del Desarrollo Humano, 2013): no refleja la situación de hoy.",
    "F18": "La tabla no dice si el distrito es el de residencia de la madre o el del lugar del parto.",
    "F19": "La tabla no dice si el distrito es el de residencia de la madre o el del lugar del parto. "
    "Cifra preliminar de la fuente (datos del 16/04/2025).",
    "F20": "La tabla no dice si el distrito es el de residencia de la madre o el del lugar del parto.",
}


# Advertencias de los indicadores calculados (no salen del Diccionario sino del método).
ADVERTENCIA_COBERTURA = (
    f"Estimación: radio de {RADIO_COBERTURA_M} m en línea recta (decisión del equipo), no distancia "
    "caminando. No cuenta estaciones de tren CPTM, que no están en el lago."
)
ADVERTENCIA_POBLACION = "Población del censo 2022 (F41); las paradas y estaciones son de la descarga actual."


# --- Filtro único de privacidad --------------------------------------------


def es_sensible(fuente_id: str, campo: str) -> bool:
    """Sensible según el Diccionario y sin una excepción del equipo en PUBLICACION_AUTORIZADA."""
    return campo in CAMPOS_SENSIBLES.get(fuente_id, set()) and (fuente_id, campo) not in PUBLICACION_AUTORIZADA


def filtrar_registros(registros: list[dict]) -> list[dict]:
    """Quita indicadores sobre campos sensibles, salvo los que salen transformados."""
    salida = []
    for r in registros:
        clave = (r["fuente_id"], r["campo_lago"])
        if es_sensible(*clave):
            forma = PUBLICACION_TRANSFORMADA.get(clave)
            if forma is None or r.get("transformacion") != forma:
                continue
        salida.append(r)
    return salida


def filtrar_propiedades(gdf: gpd.GeoDataFrame, fuente_id: str) -> gpd.GeoDataFrame:
    sensibles = [c for c in gdf.columns if es_sensible(fuente_id, c)]
    return gdf.drop(columns=sensibles)


def publicar(ruta_relativa: str, contenido, silencioso: bool = False) -> None:
    """Única puerta de salida a public/data/."""
    destino = PUBLIC_DATA / ruta_relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenido, dict) and "indicadores" in contenido:
        contenido = {**contenido, "indicadores": filtrar_registros(contenido["indicadores"])}
    # allow_nan=False: un NaN rompería el JSON en el navegador; mejor fallar aquí.
    texto = json.dumps(contenido, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    destino.write_text(texto, encoding="utf-8")
    if not silencioso:
        print(f"  public/data/{ruta_relativa}: {len(texto) / 1024:,.0f} KB")


def publicar_geo(
    ruta_relativa: str,
    gdf: gpd.GeoDataFrame,
    fuente_id: str | None,
    tolerancia_m: float = 0,
    decimales: int = 5,
    silencioso: bool = False,
) -> None:
    gdf = filtrar_propiedades(gdf, fuente_id) if fuente_id else gdf
    if tolerancia_m:
        gdf = gdf.to_crs(CRS_TRABAJO)
        # En líneas no hace falta preservar topología (es mucho más rápido); en polígonos sí.
        lineas = gdf.geom_type.isin(["LineString", "MultiLineString"]).all()
        gdf["geometry"] = gdf.geometry.simplify(tolerancia_m, preserve_topology=not lineas)
    gdf = gdf.to_crs(CRS_WEB)
    geojson = json.loads(gdf.to_json(drop_id=True))
    for f in geojson["features"]:
        f["geometry"] = redondear(f["geometry"], decimales)
    if fuente_id:
        geojson["fuente_id"] = fuente_id  # verificar.py revisa las propiedades contra esta fuente
    publicar(ruta_relativa, geojson, silencioso)


def redondear(geom: dict, decimales: int = 5) -> dict:
    """5 decimales ≈ 1 m: suficiente para el mapa y reduce el peso a la mitad."""

    def r(c):
        return [round(x, decimales) for x in c] if isinstance(c[0], float) else [r(x) for x in c]

    return {**geom, "coordinates": r(geom["coordinates"])}


# --- Contrato de indicadores (sección 6) -----------------------------------


def indicador(
    *,
    campo_lago,
    valor,
    unidad,
    nivel,
    codigo,
    nombre,
    fuente_id,
    vigencia,
    tipo="observado",
    id_extra="",
    calculo=None,
    clave=None,
    fuentes_adicionales=None,
    advertencia=None,
    transformacion=None,
) -> dict:
    """clave es el nombre del indicador en el id; por omisión, campo_lago + id_extra."""
    assert tipo in TIPOS
    clave = clave or f"{campo_lago}{id_extra}"
    registro = {
        "id": f"{clave}_{nivel}_{codigo}_{vigencia}",
        "campo_lago": campo_lago,
        "valor": None if pd.isna(valor) else round(float(valor), 4),
        "unidad": unidad,
        "nivel": nivel,
        "codigo_territorio": codigo,
        "nombre_territorio": nombre,
        "fuente_id": fuente_id,
        "vigencia": str(vigencia),
        "tipo": tipo,
        "advertencia": " ".join(a for a in (ADVERTENCIAS.get(fuente_id), advertencia) if a) or None,
    }
    if calculo:
        registro["calculo"] = calculo
    if fuentes_adicionales:
        registro["fuentes_adicionales"] = fuentes_adicionales
    if transformacion:
        # Campos Sensibles que salen transformados (config.PUBLICACION_TRANSFORMADA).
        registro["transformacion"] = transformacion
    return registro


# --- Secciones --------------------------------------------------------------


def nombres_visibles() -> tuple[dict, dict]:
    """Nombres con tildes de Infocidade («Água Rasa», «Sé») por código.

    GeoSampa los trae en mayúsculas y sin tildes; esos se quedan para unir, estos para mostrar.
    """
    lago = pd.read_csv(LAGO / "establecimientos_empleos.csv")
    lago = unir_subprefeituras(unir_distritos(lago.drop_duplicates(["unidad_territorial", "nivel"])))
    dist = lago[lago.nivel == "distrito"]
    sub = lago[lago.nivel == "subprefeitura"]
    return (
        dict(zip(dist.codigo_distrito, dist.unidad_territorial, strict=True)),
        dict(zip(sub.codigo_subprefeitura, sub.unidad_territorial, strict=True)),
    )


def construir_territorio():
    eq = cargar_equivalencias()
    vis_dist, vis_sub = nombres_visibles()
    dist = gpd.read_file(LAGO_GEO / "distritos.gpkg")
    dist = dist.merge(eq[["codigo_distrito", "subprefeitura"]], on="codigo_distrito")
    dist["nombre_visible"] = dist["codigo_distrito"].map(vis_dist).fillna(dist["nombre"].str.title())
    dist["subprefeitura"] = dist["codigo_subprefeitura"].map(vis_sub).fillna(dist["subprefeitura"].str.title())
    dist["area_km2"] = dist["area_km2"].round(2)
    publicar_geo("territorio/distritos.geojson", dist, None, tolerancia_m=15)
    sub = gpd.read_file(LAGO_GEO / "subprefeituras.gpkg")
    sub["nombre_visible"] = sub["codigo_subprefeitura"].map(vis_sub).fillna(sub["nombre"].str.title())
    sub["area_km2"] = sub["area_km2"].round(2)
    publicar_geo("territorio/subprefeituras.geojson", sub, None, tolerancia_m=15)
    publicar_geo("territorio/municipio.geojson", contorno_y_mascara(sub), None)


def contorno_y_mascara(subprefeituras: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """El borde del municipio y su negativo (el mundo menos São Paulo).

    Los mapas tapan con la máscara todo lo que queda fuera, para mostrar solo la ciudad.
    """
    union = subprefeituras.to_crs(CRS_TRABAJO).union_all().buffer(1).simplify(15)
    # Sin huecos ni astillas: solo el contorno exterior de las partes de más de 1 km².
    partes = [shapely.Polygon(p.exterior) for p in getattr(union, "geoms", [union]) if p.area > 1e6]
    municipio = gpd.GeoSeries([shapely.MultiPolygon(partes)], crs=CRS_TRABAJO).to_crs(CRS_WEB).iloc[0]
    mundo = shapely.box(-180, -85, 180, 85)
    return gpd.GeoDataFrame(
        {"parte": ["municipio", "fuera"]},
        geometry=[municipio, mundo.difference(municipio)],
        crs=CRS_WEB,
    )


def construir_empleo():
    lago = pd.read_csv(LAGO / "establecimientos_empleos.csv")
    lago = unir_subprefeituras(unir_distritos(lago))
    eq = cargar_equivalencias()
    nombres_dist, nombres_sub = nombres_visibles()
    area_dist = dict(zip(eq.codigo_distrito, eq.area_km2.astype(float), strict=True))

    # Invalidos y no localizados se quedan en el lago, pero no van a mapas ni rankings.
    lago = lago[lago["nivel"].isin(["municipio", "subprefeitura", "distrito"])]
    total_mun = lago[lago.nivel == "municipio"].set_index("anio")["empleos_formales"]

    registros = []
    campos = [("establecimientos_formales", "Establecimientos", "F11"), ("empleos_formales", "Empleos", "F12")]
    for fila in lago.itertuples():
        codigo, nombre = territorio(fila, nombres_dist, nombres_sub)
        for campo, unidad, fuente in campos:
            registros.append(
                indicador(
                    campo_lago=campo,
                    valor=getattr(fila, campo),
                    unidad=unidad,
                    nivel=fila.nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id=fuente,
                    vigencia=fila.anio,
                )
            )
        if fila.nivel == "distrito":
            registros.append(
                indicador(
                    campo_lago="empleos_formales",
                    id_extra="_participacion",
                    valor=100 * fila.empleos_formales / total_mun[fila.anio],
                    unidad="% del municipio",
                    nivel="distrito",
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id="F12",
                    vigencia=fila.anio,
                    calculo="empleos_formales del distrito / empleos_formales del municipio × 100",
                )
            )
            registros.append(
                indicador(
                    campo_lago="empleos_formales",
                    id_extra="_por_km2",
                    valor=fila.empleos_formales / area_dist[codigo],
                    unidad="Empleos por km²",
                    nivel="distrito",
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id="F12",
                    vigencia=fila.anio,
                    calculo="empleos_formales / área del distrito (GeoSampa, EPSG:31983)",
                )
            )

    registros += empleo_por_sexo(nombres_dist, nombres_sub)
    registros += empleo_por_raza(nombres_dist, nombres_sub)
    publicar_por_partes("empleo", "P2", registros)


def territorio(fila, nombres_dist: dict, nombres_sub: dict) -> tuple[str, str]:
    """Código y nombre visible de una fila de Infocidade ya unida a la tabla de equivalencias."""
    if fila.nivel == "distrito":
        return fila.codigo_distrito, nombres_dist[fila.codigo_distrito]
    if fila.nivel == "subprefeitura":
        return fila.codigo_subprefeitura, nombres_sub[fila.codigo_subprefeitura]
    return "MSP", "Município de São Paulo"


def leer_por_unidad(archivo: str) -> pd.DataFrame:
    """Tabla del lago por unidad territorial, sin inválidos ni no localizados y con sus códigos."""
    df = pd.read_csv(LAGO / archivo)
    df = df[df["nivel"].isin(["municipio", "subprefeitura", "distrito"])]
    return unir_subprefeituras(unir_distritos(df))


FUENTE_SEXO = {2024: "F13", 2023: "F14", 2022: "F15"}
FUENTE_RAZA = {2024: "F16", 2023: "F17"}
ETIQUETAS_RAZA = {
    "amarela": "amarilla",
    "branca": "blanca",
    "indigena": "indígena",
    "parda": "parda",
    "preta": "preta",
    "nao_identificada": "no identificada",
}


def empleo_por_sexo(nombres_dist: dict, nombres_sub: dict) -> list[dict]:
    registros = []
    for fila in leer_por_unidad("empleo_sexo.csv").itertuples():
        codigo, nombre = territorio(fila, nombres_dist, nombres_sub)
        total = fila.empleos_masculino + fila.empleos_femenino
        registros.append(
            indicador(
                clave="empleos_femenino_pct",
                campo_lago="empleos_femenino",
                valor=100 * fila.empleos_femenino / total if total else None,
                unidad="% de los empleos",
                nivel=fila.nivel,
                codigo=codigo,
                nombre=nombre,
                fuente_id=FUENTE_SEXO[fila.anio],
                vigencia=fila.anio,
                calculo="empleos_femenino / (empleos_masculino + empleos_femenino) × 100",
            )
        )
    return registros


def empleo_por_raza(nombres_dist: dict, nombres_sub: dict) -> list[dict]:
    """Raza o color es Sensible: sale solo como porcentaje, y se suprime bajo el umbral."""
    df = leer_por_unidad("empleo_raza.csv")
    claves = ["anio", "nivel", "unidad_territorial"]
    ancho = df.pivot_table(index=claves, columns="raza_color", values="empleos", aggfunc="sum").reset_index()
    ancho = ancho.merge(df.drop_duplicates(claves)[[*claves, "codigo_distrito", "codigo_subprefeitura"]], on=claves)
    ancho["preta_parda"] = ancho["preta"] + ancho["parda"]
    categorias = [*ETIQUETAS_RAZA, "preta_parda"]
    registros = []
    for fila in ancho.itertuples():
        codigo, nombre = territorio(fila, nombres_dist, nombres_sub)
        total = sum(getattr(fila, c) for c in ETIQUETAS_RAZA)
        for categoria in categorias:
            casos = getattr(fila, categoria)
            suprimido = casos < UMBRAL_SUPRESION
            etiqueta = ETIQUETAS_RAZA.get(categoria, "preta o parda")
            registros.append(
                indicador(
                    clave=f"empleos_raza_{categoria}_pct",
                    campo_lago="empleos",
                    valor=None if suprimido or not total else 100 * casos / total,
                    unidad="% de los empleos",
                    nivel=fila.nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id=FUENTE_RAZA[fila.anio],
                    vigencia=fila.anio,
                    calculo=f"empleos de raza o color {etiqueta} / total de empleos × 100",
                    advertencia=f"Menos de {UMBRAL_SUPRESION} empleos: la cifra se suprime." if suprimido else None,
                    transformacion="porcentaje",
                )
            )
    return registros


def publicar_por_partes(seccion: str, pregunta: str, registros: list[dict]) -> None:
    """Un archivo por año (para el mapa) y uno por territorio (para la serie).

    Así el navegador nunca baja la tabla completa.
    """
    df = pd.DataFrame(registros)
    cabecera = {"seccion": seccion, "pregunta": pregunta, "generado": dt.date.today().isoformat()}
    for anio, grupo in df.groupby("vigencia"):
        publicar(f"indicadores/{seccion}/anio_{anio}.json", {**cabecera, "indicadores": limpiar_nulos(grupo)})
    for (nivel, codigo), grupo in df.groupby(["nivel", "codigo_territorio"]):
        publicar(
            f"indicadores/{seccion}/serie_{nivel}_{codigo}.json", {**cabecera, "indicadores": limpiar_nulos(grupo)}
        )
    publicar(
        f"indicadores/{seccion}/indice.json",
        {
            **cabecera,
            "anios": sorted(df["vigencia"].unique().tolist()),
            "territorios": (
                df[["nivel", "codigo_territorio", "nombre_territorio"]].drop_duplicates().to_dict(orient="records")
            ),
        },
    )


OPCIONALES = ("calculo", "fuentes_adicionales", "transformacion")


def limpiar_nulos(df: pd.DataFrame) -> list[dict]:
    """Quita las claves opcionales vacías (calculo, fuentes_adicionales, transformacion) de cada registro."""

    def vacio(v):
        return v is None or (isinstance(v, float) and math.isnan(v))

    # Al pasar por pandas, un valor suprimido (None) vuelve como NaN, que no es JSON válido.
    return [
        {k: None if vacio(v) else v for k, v in r.items() if not (k in OPCIONALES and vacio(v))}
        for r in df.to_dict(orient="records")
    ]


def vigencia_descarga(nombre_raw: str) -> str:
    """Las capas de GeoSampa son «dato operativo actual»: su vigencia es el mes de la descarga."""
    return sorted(RAW.glob(f"*_{nombre_raw}.geojson"))[-1].name[:7]


# (clave, columna en calculos_p1, campo_lago, fuente, unidad, tipo, adicionales, cálculo)
METRICAS_P1 = [
    (
        "paradas_bus",
        "paradas_bus",
        "codigo_parada",
        "F30",
        "Paradas",
        "observado",
        None,
        "conteo de codigo_parada dentro del distrito",
    ),
    (
        "paradas_por_km2",
        "paradas_por_km2",
        "codigo_parada",
        "F30",
        "Paradas por km²",
        "observado",
        None,
        "paradas / área del distrito",
    ),
    (
        "estaciones_metro",
        "estaciones_metro",
        "id_estacion",
        "F36",
        "Estaciones",
        "observado",
        None,
        "conteo de id_estacion dentro del distrito",
    ),
    (
        "lineas_bus",
        "lineas_bus",
        "codigo_linea",
        "F29",
        "Líneas",
        "observado",
        None,
        "líneas distintas (codigo_linea) cuyo recorrido pasa por el distrito",
    ),
    (
        "km_red_bus",
        "km_red_bus",
        "codigo_linea",
        "F29",
        "km",
        "observado",
        None,
        "longitud de la unión de todos los recorridos dentro del distrito; una calle con varias líneas cuenta una vez",
    ),
    (
        "km_red_bus_por_km2",
        "km_red_bus_por_km2",
        "codigo_linea",
        "F29",
        "km de red por km²",
        "observado",
        None,
        "km de red de bus / área del distrito",
    ),
    (
        "cobertura_area",
        "cobertura_area_pct",
        "codigo_parada",
        "F30",
        "% del área",
        "estimado",
        ["F36"],
        f"área del distrito a {RADIO_COBERTURA_M} m o menos de una parada de bus o estación de metro"
        " / área del distrito",
    ),
    (
        "cobertura_poblacion",
        "cobertura_poblacion_pct",
        "poblacion",
        "F41",
        "% de la población",
        "estimado",
        ["F30", "F36"],
        f"población de los sectores censales cuyo punto interior está a {RADIO_COBERTURA_M} m o menos de una "
        "parada o estación / población del distrito",
    ),
    (
        "cobertura_poblacion_metro",
        "cobertura_poblacion_metro_pct",
        "poblacion",
        "F41",
        "% de la población",
        "estimado",
        ["F36"],
        "igual que la cobertura de población, pero solo con estaciones de metro",
    ),
    (
        "poblacion",
        "poblacion",
        "poblacion",
        "F41",
        "Personas",
        "observado",
        None,
        "suma de poblacion de los sectores censales del distrito (codigo_distrito)",
    ),
    (
        "densidad",
        "densidad_hab_km2",
        "poblacion",
        "F41",
        "Habitantes por km²",
        "observado",
        None,
        "población / área del distrito",
    ),
]


def construir_transporte():
    cobertura = calculos_p1.cobertura_por_distrito()
    nombres_dist, _ = nombres_visibles()
    vig_red = vigencia_descarga("geosampa_ponto_onibus")
    registros = []
    for codigo, fila in cobertura.iterrows():
        nivel = "municipio" if codigo == "MSP" else "distrito"
        nombre = "Município de São Paulo" if codigo == "MSP" else nombres_dist[codigo]
        for clave, columna, campo, fuente, unidad, tipo, adicionales, calculo in METRICAS_P1:
            # Solo la población sale entera del censo; lo que cruza con la red es de la descarga actual.
            vigencia = "2022" if fuente == "F41" and adicionales is None else vig_red
            advertencia = ADVERTENCIA_COBERTURA if clave.startswith("cobertura") else None
            if clave.startswith("cobertura_poblacion"):
                advertencia = f"{ADVERTENCIA_COBERTURA} {ADVERTENCIA_POBLACION}"
            registros.append(
                indicador(
                    clave=clave,
                    campo_lago=campo,
                    valor=fila[columna],
                    unidad=unidad,
                    nivel=nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id=fuente,
                    vigencia=vigencia,
                    tipo=tipo,
                    calculo=calculo,
                    fuentes_adicionales=adicionales,
                    advertencia=advertencia,
                )
            )
    cabecera = {
        "seccion": "transporte",
        "pregunta": "P1",
        "generado": dt.date.today().isoformat(),
        "radio_cobertura_m": RADIO_COBERTURA_M,
    }
    publicar("indicadores/transporte/distritos.json", {**cabecera, "indicadores": registros})

    construir_pasajeros(cabecera)

    # Capas del mapa 3D (capa B). La red de bus va sin atributos (cada calle una vez) y,
    # como las paradas, partida en celdas: el mapa baja solo las que ve al acercarse.
    publicar_por_celdas("transporte/red_bus", calculos_p1.red_bus(), "F29", tolerancia_m=10)
    paradas = calculos_p1.capa("paradas")[["codigo_parada", "calle_numero", "geometry"]]
    publicar_por_celdas("transporte/paradas", paradas, "F30")
    publicar_geo("transporte/metro.geojson", calculos_p1.capa("metro"), "F35", tolerancia_m=5)
    publicar_geo("transporte/tren.geojson", calculos_p1.capa("tren"), "F31", tolerancia_m=5)
    publicar_geo("transporte/estaciones.geojson", calculos_p1.capa("estaciones"), "F36")


def construir_pasajeros(cabecera: dict):
    ruta = LAGO / "sptrans_pasajeros.csv"
    if not ruta.exists():
        print("  (sin lago/sptrans_pasajeros.csv: corre pull_movilidad.py sin --sin-pasajeros)")
        return
    df = pd.read_csv(ruta, dtype={"codigo_linea": str})
    df["periodo"] = df["anio"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2)
    registros = []
    # Serie mensual del sistema (no se reparte por distrito: F05 no tiene geografía).
    for periodo, total in df.groupby("periodo")["pasajeros_total"].sum().items():
        registros.append(
            indicador(
                clave="pasajeros_total_mes",
                campo_lago="pasajeros_total",
                valor=total,
                unidad="Pasajeros",
                nivel="municipio",
                codigo="MSP",
                nombre="Sistema municipal de buses",
                fuente_id="F05",
                vigencia=periodo,
                calculo="suma de pasajeros_total de todas las líneas en el mes",
            )
        )
    # Ranking de líneas en los últimos 12 meses completos.
    meses = sorted(df["periodo"].unique())[-12:]
    ventana = f"{meses[0]} a {meses[-1]}"
    ultimos = df[df["periodo"].isin(meses)]
    por_linea = (
        ultimos.sort_values("periodo")
        .groupby("codigo_linea")
        .agg(nombre=("nombre_linea", "last"), total=("pasajeros_total", "sum"))
        .sort_values("total", ascending=False)
    )
    for codigo, fila in por_linea.iterrows():
        registros.append(
            indicador(
                clave="pasajeros_total_12m",
                campo_lago="pasajeros_total",
                valor=fila.total,
                unidad="Pasajeros",
                nivel="linea",
                codigo=codigo,
                nombre=fila.nombre or codigo,
                fuente_id="F05",
                vigencia=ventana,
                calculo=f"suma de pasajeros_total de la línea, {len(meses)} meses",
            )
        )
    publicar("indicadores/transporte/pasajeros.json", {**cabecera, "meses": meses, "indicadores": registros})


# Celdas de 0,05° (unos 5 km): a zoom 14 la pantalla cubre unas cuatro.
TAMANO_CELDA = 0.05


def publicar_por_celdas(carpeta: str, gdf: gpd.GeoDataFrame, fuente_id: str, tolerancia_m: float = 0) -> None:
    """Parte una capa en celdas de una cuadrícula y publica un archivo por celda más un índice.

    Las líneas se cortan en el borde de cada celda; los puntos van a la celda que los contiene.
    """
    if tolerancia_m:
        gdf = gdf.to_crs(CRS_TRABAJO)
        gdf["geometry"] = gdf.geometry.simplify(tolerancia_m, preserve_topology=False)
    gdf = gdf.to_crs(CRS_WEB)
    oeste, sur, este, norte = gdf.total_bounds
    celdas = []
    for x in range(math.floor(oeste / TAMANO_CELDA), math.floor(este / TAMANO_CELDA) + 1):
        for y in range(math.floor(sur / TAMANO_CELDA), math.floor(norte / TAMANO_CELDA) + 1):
            caja = shapely.box(x * TAMANO_CELDA, y * TAMANO_CELDA, (x + 1) * TAMANO_CELDA, (y + 1) * TAMANO_CELDA)
            if (gdf.geom_type == "Point").all():
                parte = gdf[gdf.geometry.x.floordiv(TAMANO_CELDA).eq(x) & gdf.geometry.y.floordiv(TAMANO_CELDA).eq(y)]
            else:
                parte = gdf.clip(caja, keep_geom_type=True)
            parte = parte[parte.geometry.notna() & ~parte.geometry.is_empty]
            if parte.empty:
                continue
            publicar_geo(f"{carpeta}/{x}_{y}.geojson", parte, fuente_id, silencioso=True)
            celdas.append(f"{x}_{y}")
    publicar(f"{carpeta}/indice.json", {"fuente_id": fuente_id, "tamano_celda": TAMANO_CELDA, "celdas": celdas})


def construir_equipamientos():
    """P1, segunda parte: escuelas, deporte, ferias y shoppings por distrito."""
    res, vigencias = calculos_equipamientos.equipamientos_por_distrito()
    nombres_dist, _ = nombres_visibles()
    vig = {
        "F33": vigencia_descarga("geosampa_centros_esportivos"),
        "F34": vigencia_descarga("geosampa_estadios"),
        "F39": vigencia_descarga("geosampa_educacao_infantil"),
        "F40": vigencia_descarga("geosampa_educacao_rede_publica"),
        **vigencias,
    }
    por_10mil = "por 10 mil habitantes (población del censo 2022, F41)"
    # (clave, columna, campo_lago, fuente, unidad, tipo, adicionales, cálculo)
    metricas = [
        (
            "escuelas_infantil",
            "escuelas_infantil",
            "codigo_equipamento",
            "F39",
            "Escuelas",
            "observado",
            None,
            "escuelas públicas de educación infantil dentro del distrito",
        ),
        (
            "escuelas_infantil_por_10mil",
            "escuelas_infantil_por_10mil",
            "codigo_equipamento",
            "F39",
            "Escuelas por 10 mil hab.",
            "observado",
            ["F41"],
            f"escuelas de educación infantil {por_10mil}",
        ),
        (
            "escuelas_basica",
            "escuelas_basica",
            "codigo_equipamento",
            "F40",
            "Escuelas",
            "observado",
            None,
            "escuelas públicas de enseñanza fundamental y media dentro del distrito",
        ),
        (
            "escuelas_basica_por_10mil",
            "escuelas_basica_por_10mil",
            "codigo_equipamento",
            "F40",
            "Escuelas por 10 mil hab.",
            "observado",
            ["F41"],
            f"escuelas de enseñanza fundamental y media {por_10mil}",
        ),
        (
            "centros_deportivos",
            "centros_deportivos",
            "id_equipamiento",
            "F33",
            "Centros",
            "observado",
            None,
            "centros deportivos y balnearios dentro del distrito",
        ),
        (
            "estadios",
            "estadios",
            "id_equipamiento",
            "F34",
            "Estadios",
            "observado",
            None,
            "clubes con estadio dentro del distrito",
        ),
        (
            "ferias",
            "ferias",
            "cantidad",
            "F21",
            "Ferias",
            "observado",
            None,
            "ferias libres del distrito según la tabla de Infocidade",
        ),
        (
            "ferias_por_10mil",
            "ferias_por_10mil",
            "cantidad",
            "F21",
            "Ferias por 10 mil hab.",
            "observado",
            ["F41"],
            f"ferias libres {por_10mil}",
        ),
        (
            "mercados",
            "mercados",
            "cantidad",
            "F21",
            "Mercados",
            "observado",
            None,
            "mercados y sacolões municipales del distrito",
        ),
        (
            "shoppings",
            "shoppings",
            "id_shopping",
            "F22",
            "Shoppings",
            "observado",
            None,
            "shoppings del censo de ABRASCE ubicados en el distrito",
        ),
        (
            "abl_shoppings",
            "abl_shoppings_m2",
            "abl_m2",
            "F22",
            "m² de ABL",
            "observado",
            None,
            "suma del área bruta locable de los shoppings del distrito",
        ),
    ]
    registros = []
    for codigo, fila in res.iterrows():
        nivel = "municipio" if codigo == "MSP" else "distrito"
        nombre = "Município de São Paulo" if codigo == "MSP" else nombres_dist[codigo]
        for clave, columna, campo, fuente, unidad, tipo, adicionales, calculo in metricas:
            registros.append(
                indicador(
                    clave=clave,
                    campo_lago=campo,
                    valor=fila[columna],
                    unidad=unidad,
                    nivel=nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id=fuente,
                    vigencia=vig[fuente],
                    tipo=tipo,
                    calculo=calculo,
                    fuentes_adicionales=adicionales,
                )
            )
    cabecera = {"seccion": "equipamientos", "pregunta": "P1", "generado": dt.date.today().isoformat()}
    publicar("indicadores/equipamientos/distritos.json", {**cabecera, "indicadores": registros})

    capas = {
        "escuelas_infantil": ("F39", ["codigo_equipamento", "nombre", "direccion"]),
        "escuelas_basica": ("F40", ["codigo_equipamento", "nombre", "direccion"]),
        "centros_deportivos": ("F33", ["nombre", "tipo", "direccion"]),
        "estadios": ("F34", ["nombre", "tipo", "direccion"]),
    }
    for nombre, (fuente, columnas) in capas.items():
        gdf = calculos_p1.capa(nombre)
        publicar_geo(f"equipamientos/{nombre}.geojson", gdf[[*columnas, "geometry"]], fuente)


ADVERTENCIA_DOMICILIOS_FAVELA = "No se sabe si los domicilios de la capa son un conteo o una estimación de HABITASAMPA."


def construir_gente():
    """Favelas por distrito (F32) y área construida residencial del municipio (F28)."""
    res = calculos_equipamientos.favelas_por_distrito()
    nombres_dist, _ = nombres_visibles()
    vig = vigencia_descarga("geosampa_favelas")
    metricas = [
        (
            "favelas",
            "favelas",
            "id_favela",
            "Favelas",
            "observado",
            None,
            "favelas cuya mayor parte está en el distrito",
        ),
        (
            "domicilios_favela",
            "domicilios_favela",
            "domicilios",
            "Domicilios",
            "estimado",
            None,
            "domicilios de las favelas del distrito; una favela que cruza el límite se reparte por área",
        ),
        (
            "domicilios_favela_pct",
            "domicilios_favela_pct",
            "domicilios",
            "% de los domicilios",
            "estimado",
            ["F41"],
            "domicilios en favelas / domicilios del censo 2022 (F41) × 100",
        ),
        (
            "area_favela_pct",
            "area_favela_pct",
            "area_m2",
            "% del área",
            "observado",
            None,
            "área de favelas en el distrito / área del distrito × 100",
        ),
    ]
    registros = []
    for codigo, fila in res.iterrows():
        nivel = "municipio" if codigo == "MSP" else "distrito"
        nombre = "Município de São Paulo" if codigo == "MSP" else nombres_dist[codigo]
        for clave, columna, campo, unidad, tipo, adicionales, calculo in metricas:
            registros.append(
                indicador(
                    clave=clave,
                    campo_lago=campo,
                    valor=fila[columna],
                    unidad=unidad,
                    nivel=nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id="F32",
                    vigencia=vig,
                    tipo=tipo,
                    calculo=calculo,
                    fuentes_adicionales=adicionales,
                    advertencia=ADVERTENCIA_DOMICILIOS_FAVELA if campo == "domicilios" else None,
                )
            )
    cabecera = {"seccion": "gente", "pregunta": "", "generado": dt.date.today().isoformat()}
    publicar("indicadores/gente/distritos.json", {**cabecera, "indicadores": registros})

    area = pd.read_csv(LAGO / "area_construida_residencial.csv")
    serie = [
        indicador(
            campo_lago="area_residencial_m2",
            valor=fila.area_residencial_m2 / 1e6,
            unidad="km²",
            nivel="municipio",
            codigo="MSP",
            nombre="Município de São Paulo",
            fuente_id="F28",
            vigencia=fila.anio,
            calculo="área construida residencial del catastro del IPTU (enero de cada año) / 1.000.000",
        )
        for fila in area.itertuples()
    ]
    publicar("indicadores/gente/area_construida.json", {**cabecera, "indicadores": serie})

    construir_poblacion_historica(cabecera)
    construir_idhm(cabecera)
    construir_nacimientos(cabecera)

    # Con el nombre (excepción del equipo en config.PUBLICACION_AUTORIZADA), pero sin la calle ni la
    # propiedad del terreno, que son Sensibles: publicar_geo los quita.
    publicar_geo("gente/favelas.geojson", calculos_p1.capa("favelas"), "F32", tolerancia_m=3)


# (campo del lago, nivel, código, nombre). Las cuatro columnas de F01 son cuatro territorios distintos.
TERRITORIOS_F01 = [
    ("poblacion_brasil", "pais", "BR", "Brasil"),
    ("poblacion_estado_sp", "estado", "SP", "Estado de São Paulo"),
    ("poblacion_rm_sp", "region_metropolitana", "RMSP", "Região Metropolitana de São Paulo"),
    ("poblacion_municipio_sp", "municipio", "MSP", "Município de São Paulo"),
]
ADVERTENCIA_RM = "La Región Metropolitana se creó en 1973: la fuente trae su cifra desde 1980."


def construir_poblacion_historica(cabecera: dict):
    """F01: población de cada censo desde 1872. Las cifras que la fuente no tiene (RM antes de 1980) no se publican."""
    df = pd.read_csv(LAGO / "poblacion_historica.csv")
    registros = []
    for fila in df.itertuples():
        for campo, nivel, codigo, nombre in TERRITORIOS_F01:
            valor = getattr(fila, campo)
            if pd.isna(valor):
                continue
            registros.append(
                indicador(
                    clave="poblacion_historica",
                    campo_lago=campo,
                    valor=valor,
                    unidad="Personas",
                    nivel=nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id="F01",
                    vigencia=fila.anio,
                    advertencia=ADVERTENCIA_RM if nivel == "region_metropolitana" else None,
                )
            )
    publicar("indicadores/gente/poblacion_historica.json", {**cabecera, "indicadores": registros})


# La Subprefeitura de Sapopemba se creó en 2013, después del Atlas: en F07 «Vila Prudente» la incluye.
CODIGO_VILA_PRUDENTE = "29"
ADVERTENCIA_VILA_PRUDENTE = (
    "En esta fuente la Prefeitura Regional de Vila Prudente incluye el distrito de Sapopemba, "
    "que desde 2013 es una subprefeitura aparte y no tiene cifra propia."
)


def construir_idhm(cabecera: dict):
    """F07: IDHM y IDHM Renda de 2000 y 2010 por Prefeitura Regional, que equivale a la subprefeitura."""
    df = pd.read_csv(LAGO / "idhm.csv")
    df["nivel"] = df["prefeitura_regional"].map(lambda n: "municipio" if n == "MSP" else "subprefeitura")
    df = unir_subprefeituras(df, "prefeitura_regional")
    _, nombres_sub = nombres_visibles()
    registros = []
    for fila in df.itertuples():
        if fila.nivel == "municipio":
            codigo, nombre = "MSP", "Município de São Paulo"
        else:
            codigo = fila.codigo_subprefeitura
            nombre = nombres_sub[codigo]
        advertencia = ADVERTENCIA_VILA_PRUDENTE if codigo == CODIGO_VILA_PRUDENTE else None
        for campo in ("idhm", "idhm_renda"):
            registros.append(
                indicador(
                    campo_lago=campo,
                    valor=getattr(fila, campo),
                    unidad="Índice 0–1",
                    nivel=fila.nivel,
                    codigo=codigo,
                    nombre=nombre,
                    fuente_id="F07",
                    vigencia=fila.anio,
                    advertencia=advertencia,
                )
            )
    publicar("indicadores/gente/idhm.json", {**cabecera, "indicadores": registros})


FUENTE_NACIMIENTOS = {2025: "F18", 2024: "F19", 2023: "F20"}
# Desde este porcentaje de nacimientos sin distrito, las cifras por distrito llevan la advertencia.
UMBRAL_SIN_UBICACION_PCT = 1
ADVERTENCIA_POBLACION_TASA = "La población es la del censo 2022, no la del año de los nacimientos."


def poblacion_censo_por_distrito() -> pd.Series:
    """Población del censo 2022 (F41) por código de distrito."""
    sectores = gpd.read_file(
        LAGO_GEO / "densidad_sectores.geojson", columns=["codigo_distrito", "poblacion"], ignore_geometry=True
    )
    return sectores.groupby("codigo_distrito")["poblacion"].sum()


def construir_nacimientos(cabecera: dict):
    """F18-F20: nacidos vivos por distrito y año, y por mil habitantes.

    tipo_parto es Sensible: el total es la suma de los tres tipos y el tipo no sale del lago.
    """
    df = pd.read_csv(LAGO / "nacimientos_tipo_parto.csv")
    total = df.groupby(["anio", "nivel", "unidad_territorial"], as_index=False)["nacidos_vivos"].sum()
    total = unir_distritos(total)
    nombres_dist, _ = nombres_visibles()
    poblacion = poblacion_censo_por_distrito()
    registros = []
    for anio, grupo in total.groupby("anio"):
        fuente = FUENTE_NACIMIENTOS[anio]
        en_municipio = int(grupo.loc[grupo["nivel"] == "municipio", "nacidos_vivos"].iloc[0])
        sin_distrito = int(grupo.loc[grupo["nivel"] == "sin_ubicacion", "nacidos_vivos"].iloc[0])
        pct_sin = 100 * sin_distrito / en_municipio
        aviso = None
        if pct_sin >= UMBRAL_SIN_UBICACION_PCT:
            porcentaje = f"{pct_sin:.1f}".replace(".", ",")
            aviso = (
                f"El {porcentaje} % de los nacimientos del año no tiene distrito conocido y no entra en las cifras "
                "por distrito, que por eso quedan por debajo de lo real."
            )
        territorios = [("municipio", "MSP", "Município de São Paulo", en_municipio, int(poblacion.sum()), None)]
        for fila in grupo[grupo["nivel"] == "distrito"].itertuples():
            codigo = fila.codigo_distrito
            territorios.append(
                ("distrito", codigo, nombres_dist[codigo], int(fila.nacidos_vivos), int(poblacion[codigo]), aviso)
            )
        comunes = {"fuente_id": fuente, "vigencia": anio}
        for nivel, codigo, nombre, nacidos, habitantes, advertencia in territorios:
            territorio = {"nivel": nivel, "codigo": codigo, "nombre": nombre}
            registros.append(
                indicador(
                    campo_lago="nacidos_vivos",
                    valor=nacidos,
                    unidad="Nacimientos",
                    calculo="suma de los nacidos vivos de los tres tipos de parto (vaginal, cesárea e ignorado)",
                    advertencia=advertencia,
                    **territorio,
                    **comunes,
                )
            )
            registros.append(
                indicador(
                    clave="nacidos_vivos_por_mil_hab",
                    campo_lago="nacidos_vivos",
                    valor=1000 * nacidos / habitantes,
                    unidad="Nacimientos por mil hab.",
                    tipo="estimado",
                    calculo="nacidos vivos del año / población del censo 2022 (F41) × 1.000",
                    fuentes_adicionales=["F41"],
                    advertencia=" ".join(a for a in (ADVERTENCIA_POBLACION_TASA, advertencia) if a),
                    **territorio,
                    **comunes,
                )
            )
        registros.append(
            indicador(
                clave="nacidos_vivos_sin_ubicacion_pct",
                campo_lago="nacidos_vivos",
                valor=pct_sin,
                unidad="% de los nacimientos",
                nivel="municipio",
                codigo="MSP",
                nombre="Município de São Paulo",
                calculo="nacidos vivos de la fila sin distrito / nacidos vivos del municipio × 100",
                **comunes,
            )
        )
    publicar("indicadores/gente/nacimientos.json", {**cabecera, "indicadores": registros})


FUENTE_VEGETACION = {2020: "F25", 2015: "F26", 2010: "F27"}


def construir_ambiente():
    """Cobertura vegetal por habitante por subprefeitura (F25-F27). Cada año es un método distinto."""
    df = pd.read_csv(LAGO / "cobertura_vegetal.csv")
    df = unir_subprefeituras(df)
    _, nombres_sub = nombres_visibles()
    registros = []
    for fila in df.itertuples():
        codigo = "MSP" if fila.nivel == "municipio" else fila.codigo_subprefeitura
        nombre = "Município de São Paulo" if codigo == "MSP" else nombres_sub[codigo]
        fuente = FUENTE_VEGETACION[fila.anio]
        comunes = {"nivel": fila.nivel, "codigo": codigo, "nombre": nombre, "fuente_id": fuente, "vigencia": fila.anio}
        registros.append(
            indicador(
                clave="cobertura_vegetal_por_hab",
                campo_lago="cobertura_vegetal_m2",
                valor=fila.cobertura_vegetal_m2 / fila.poblacion,
                unidad="m² por habitante",
                calculo="cobertura_vegetal_m2 / poblacion (de la misma tabla)",
                **comunes,
            )
        )
        registros.append(
            indicador(
                clave="cobertura_vegetal_km2",
                campo_lago="cobertura_vegetal_m2",
                valor=fila.cobertura_vegetal_m2 / 1e6,
                unidad="km²",
                calculo=f"cobertura_vegetal_m2 / 1.000.000; método: {fila.metodo_cobertura}",
                **comunes,
            )
        )
    cabecera = {"seccion": "ambiente", "pregunta": "", "generado": dt.date.today().isoformat()}
    publicar("indicadores/ambiente/subprefeituras.json", {**cabecera, "indicadores": registros})


# Normal climatológica de la OMM: promedio de 30 años seguidos. La fuente publica la de 1991-2020.
NORMAL_DESDE, NORMAL_HASTA = 1991, 2020
ESTACION_F06 = "Estación del IAG en Água Funda"


def construir_temperatura():
    """Temperatura mínima media del aire (F06): por mes, por año, normal 1991-2020 y diferencia con la normal.

    Es una sola estación meteorológica (IAG, USP), no la ciudad: la advertencia de F06 sale en cada cifra.
    Las normales y los promedios anuales se recalculan de los doce meses de cada año.
    """
    df = pd.read_csv(LAGO / "temperatura_minima.csv")
    comunes = {
        "campo_lago": "temp_min_media_c",
        "unidad": "°C",
        "nivel": "municipio",
        "codigo": "MSP",
        "nombre": ESTACION_F06,
        "fuente_id": "F06",
    }
    registros = []
    for fila in df.itertuples():
        registros.append(
            indicador(
                clave="temp_min_mes", valor=fila.temp_min_media_c, vigencia=f"{fila.anio}-{fila.mes:02d}", **comunes
            )
        )

    anual = df.groupby("anio")["temp_min_media_c"].agg(["mean", "count"])
    anual = anual[anual["count"] == 12]["mean"]  # solo años con los doce meses
    for anio, valor in anual.items():
        registros.append(
            indicador(
                clave="temp_min_anual",
                valor=valor,
                vigencia=anio,
                calculo="promedio de los 12 promedios mensuales del año",
                **comunes,
            )
        )

    ventana = f"{NORMAL_DESDE}-{NORMAL_HASTA}"
    de_la_normal = df[df["anio"].between(NORMAL_DESDE, NORMAL_HASTA)]
    if not (de_la_normal.groupby("mes").size() == NORMAL_HASTA - NORMAL_DESDE + 1).all():
        raise ValueError(f"F06: faltan meses en los años de la normal {ventana}")
    normal_mes = de_la_normal.groupby("mes")["temp_min_media_c"].mean()
    for mes, valor in normal_mes.items():
        registros.append(
            indicador(
                clave=f"temp_min_normal_m{mes:02d}",
                valor=valor,
                vigencia=ventana,
                calculo=f"promedio de ese mes en los {NORMAL_HASTA - NORMAL_DESDE + 1} años {ventana}",
                **comunes,
            )
        )
    normal_anual = normal_mes.mean()
    registros.append(
        indicador(
            clave="temp_min_normal_anual",
            valor=normal_anual,
            vigencia=ventana,
            calculo=f"promedio de las 12 normales mensuales {ventana}",
            **comunes,
        )
    )
    for anio, valor in anual.items():
        registros.append(
            indicador(
                clave="temp_min_anual_vs_normal",
                valor=valor - normal_anual,
                vigencia=anio,
                calculo=f"promedio anual del año menos la normal {ventana}",
                **comunes,
            )
        )
    cabecera = {"seccion": "ambiente", "pregunta": "", "generado": dt.date.today().isoformat()}
    publicar("indicadores/ambiente/temperatura.json", {**cabecera, "indicadores": registros})


def construir_catalogo():
    fuentes = pd.read_csv(FUENTES_CSV, dtype=str).fillna("")
    dicc = pd.read_csv(DICCIONARIO_CSV, dtype=str).fillna("")
    publicar("catalogo/fuentes.json", fuentes.to_dict(orient="records"))
    publicar("catalogo/diccionario.json", dicc.to_dict(orient="records"))


def main():
    if PUBLIC_DATA.exists():
        shutil.rmtree(PUBLIC_DATA)
    construir_catalogo()
    construir_territorio()
    construir_empleo()
    construir_transporte()
    construir_equipamientos()
    construir_gente()
    construir_ambiente()
    construir_temperatura()


if __name__ == "__main__":
    main()
