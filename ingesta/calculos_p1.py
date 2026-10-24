"""P1: cobertura de transporte por distrito (sección 9 del plan).

Todo se mide en EPSG:31983 (metros). Los resultados son derivados, no campos del lago:
build_web.py los publica con su cálculo y data/derivados/ guarda una copia para revisar.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import shapely

from config import DATA, LAGO_GEO, RADIO_COBERTURA_M

DERIVADOS = DATA / "derivados"


def capa(nombre: str) -> gpd.GeoDataFrame:
    return gpd.read_file(LAGO_GEO / f"{nombre}.geojson")


def cobertura_por_distrito() -> pd.DataFrame:
    distritos = gpd.read_file(LAGO_GEO / "distritos.gpkg")[["codigo_distrito", "area_km2", "geometry"]]
    paradas = capa("paradas")
    estaciones = capa("estaciones")
    buses = capa("buses")
    sectores = capa("densidad_sectores")[["codigo_sector", "codigo_distrito", "poblacion", "geometry"]]

    res = distritos.drop(columns="geometry").set_index("codigo_distrito")

    # Conteos por cruce espacial (punto dentro del distrito).
    def contar(puntos: gpd.GeoDataFrame, columna: str) -> pd.Series:
        j = gpd.sjoin(puntos, distritos, predicate="within", how="inner")
        return j.groupby("codigo_distrito")[columna].nunique()

    res["paradas_bus"] = contar(paradas, "codigo_parada")
    res["estaciones_metro"] = contar(estaciones, "id_estacion")
    lineas = gpd.sjoin(buses, distritos, predicate="intersects", how="inner")
    res["lineas_bus"] = lineas.groupby("codigo_distrito")["codigo_linea"].nunique()

    # Red de bus sin duplicar calles: unión de todos los recorridos, cortada por distrito.
    tramos = gpd.overlay(red_bus(), distritos, how="intersection", keep_geom_type=True)
    res["km_red_bus"] = tramos.assign(km=tramos.length / 1000).groupby("codigo_distrito")["km"].sum()

    # Cobertura de área: parte del distrito a RADIO o menos de una parada o estación.
    puntos = pd.concat([paradas.geometry, estaciones.geometry], ignore_index=True)
    zona = gpd.GeoDataFrame(geometry=[puntos.buffer(RADIO_COBERTURA_M).union_all()], crs=paradas.crs)
    cubierto = gpd.overlay(distritos, zona, how="intersection", keep_geom_type=True)
    res["area_cubierta_km2"] = cubierto.assign(a=cubierto.area / 1e6).groupby("codigo_distrito")["a"].sum()

    # Cobertura de población: sectores cuyo punto interior está a RADIO o menos.
    centros = sectores.copy()
    centros["geometry"] = sectores.geometry.representative_point()

    def poblacion_cubierta(destinos: gpd.GeoSeries) -> pd.Series:
        dest = gpd.GeoDataFrame(geometry=destinos.reset_index(drop=True), crs=paradas.crs)
        j = gpd.sjoin(centros, dest, predicate="dwithin", distance=RADIO_COBERTURA_M, how="inner")
        cubiertos = centros[centros["codigo_sector"].isin(j["codigo_sector"])]
        return cubiertos.groupby("codigo_distrito")["poblacion"].sum()

    res["poblacion"] = sectores.groupby("codigo_distrito")["poblacion"].sum()
    res["poblacion_cubierta"] = poblacion_cubierta(puntos)
    res["poblacion_cubierta_metro"] = poblacion_cubierta(estaciones.geometry)

    res = res.fillna(0)
    res["paradas_por_km2"] = res["paradas_bus"] / res["area_km2"]
    res["km_red_bus_por_km2"] = res["km_red_bus"] / res["area_km2"]
    res["cobertura_area_pct"] = 100 * res["area_cubierta_km2"] / res["area_km2"]
    res["cobertura_poblacion_pct"] = 100 * res["poblacion_cubierta"] / res["poblacion"]
    res["cobertura_poblacion_metro_pct"] = 100 * res["poblacion_cubierta_metro"] / res["poblacion"]
    res["densidad_hab_km2"] = res["poblacion"] / res["area_km2"]

    # Totales del municipio (sumas, no promedios de porcentajes).
    total = {
        "area_km2": res["area_km2"].sum(),
        # Solo las paradas dentro de los 96 distritos (unas pocas de la capa caen fuera).
        "paradas_bus": res["paradas_bus"].sum(),
        "estaciones_metro": res["estaciones_metro"].sum(),
        "lineas_bus": buses["codigo_linea"].nunique(),
        "km_red_bus": res["km_red_bus"].sum(),
        "area_cubierta_km2": res["area_cubierta_km2"].sum(),
        "poblacion": res["poblacion"].sum(),
        "poblacion_cubierta": res["poblacion_cubierta"].sum(),
        "poblacion_cubierta_metro": res["poblacion_cubierta_metro"].sum(),
    }
    total["paradas_por_km2"] = total["paradas_bus"] / total["area_km2"]
    total["km_red_bus_por_km2"] = total["km_red_bus"] / total["area_km2"]
    total["cobertura_area_pct"] = 100 * total["area_cubierta_km2"] / total["area_km2"]
    total["cobertura_poblacion_pct"] = 100 * total["poblacion_cubierta"] / total["poblacion"]
    total["cobertura_poblacion_metro_pct"] = 100 * total["poblacion_cubierta_metro"] / total["poblacion"]
    total["densidad_hab_km2"] = total["poblacion"] / total["area_km2"]
    res.loc["MSP"] = pd.Series(total)

    DERIVADOS.mkdir(parents=True, exist_ok=True)
    res.round(4).to_csv(DERIVADOS / "cobertura_transporte_distrito.csv")
    return res


def red_bus() -> gpd.GeoDataFrame:
    """La red de bus sin recorridos repetidos, partida en tramos (una fila por tramo).

    La unión de los 2.326 recorridos tarda; se guarda en data/derivados/ y se reutiliza
    mientras lago/geo/buses.geojson no cambie.
    """
    origen = LAGO_GEO / "buses.geojson"
    cache = DERIVADOS / "red_bus.gpkg"
    if cache.exists() and cache.stat().st_mtime > origen.stat().st_mtime:
        return gpd.read_file(cache)
    buses = capa("buses")
    union = shapely.line_merge(buses.geometry.union_all())
    red = gpd.GeoDataFrame(geometry=[union], crs=buses.crs).explode(index_parts=False).reset_index(drop=True)
    DERIVADOS.mkdir(parents=True, exist_ok=True)
    red.to_file(cache, driver="GPKG")
    return red


if __name__ == "__main__":
    print(cobertura_por_distrito().loc["MSP"])
