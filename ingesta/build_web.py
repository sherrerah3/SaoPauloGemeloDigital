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
    PUBLICACION_TRANSFORMADA,
    RADIO_COBERTURA_M,
    RAW,
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
    "F25": "El método de medición cambia entre años; no comparar 2010, 2015 y 2020.",
    "F26": "El método de medición cambia entre años; no comparar 2010, 2015 y 2020.",
    "F27": "El método de medición cambia entre años; no comparar 2010, 2015 y 2020.",
}


# Advertencias de los indicadores calculados (no salen del Diccionario sino del método).
ADVERTENCIA_COBERTURA = (
    f"Estimación: radio de {RADIO_COBERTURA_M} m en línea recta (decisión del equipo), no distancia "
    "caminando. No cuenta estaciones de tren CPTM, que no están en el lago."
)
ADVERTENCIA_POBLACION = "Población del censo 2022 (F41); las paradas y estaciones son de la descarga actual."


# --- Filtro único de privacidad --------------------------------------------


def es_sensible(fuente_id: str, campo: str) -> bool:
    return campo in CAMPOS_SENSIBLES.get(fuente_id, set())


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


def publicar(ruta_relativa: str, contenido) -> None:
    """Única puerta de salida a public/data/."""
    destino = PUBLIC_DATA / ruta_relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenido, dict) and "indicadores" in contenido:
        contenido = {**contenido, "indicadores": filtrar_registros(contenido["indicadores"])}
    texto = json.dumps(contenido, ensure_ascii=False, separators=(",", ":"))
    destino.write_text(texto, encoding="utf-8")
    print(f"  public/data/{ruta_relativa}: {len(texto) / 1024:,.0f} KB")


def publicar_geo(
    ruta_relativa: str, gdf: gpd.GeoDataFrame, fuente_id: str | None, tolerancia_m: float = 0, decimales: int = 5
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
    publicar(ruta_relativa, geojson)


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
        if fila.nivel == "distrito":
            codigo, nombre = fila.codigo_distrito, nombres_dist[fila.codigo_distrito]
        elif fila.nivel == "subprefeitura":
            codigo, nombre = fila.codigo_subprefeitura, nombres_sub[fila.codigo_subprefeitura]
        else:
            codigo, nombre = "MSP", "Município de São Paulo"
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

    publicar_por_partes("empleo", "P2", registros)


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


def limpiar_nulos(df: pd.DataFrame) -> list[dict]:
    """Quita las claves opcionales vacías (calculo, fuentes_adicionales) de cada registro."""

    def vacio(v):
        return v is None or (isinstance(v, float) and math.isnan(v))

    return [
        {k: v for k, v in r.items() if not (k in ("calculo", "fuentes_adicionales") and vacio(v))}
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

    # Capas del mapa 3D (capa B). La red de bus va como una sola geometría sin atributos.
    publicar_geo("transporte/red_bus.geojson", calculos_p1.red_bus(), "F29", tolerancia_m=10)
    paradas = calculos_p1.capa("paradas")[["codigo_parada", "calle_numero", "geometry"]]
    publicar_geo("transporte/paradas.geojson", paradas, "F30")
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


if __name__ == "__main__":
    main()
